"""Configure PostgreSQL, initialize the first admin privately, then publish Metabase."""
import base64
import json
import os
from pathlib import Path
import re
import signal
import ssl
import subprocess
import time
from urllib.parse import quote, unquote, urlencode, urlsplit
from urllib.request import Request, urlopen


def configuration(env, ca_path="/tmp/metabase-ca.pem"):
    local = env.get("LOCAL_DEVELOPMENT") == "true"
    uri = urlsplit(env.get("DATABASE_URL", ""))
    if uri.scheme not in ("postgres", "postgresql") or not uri.hostname or not uri.username or not uri.password:
        raise ValueError("DATABASE_URL must be a PostgreSQL URI with host, database, user and password.")
    database = unquote(uri.path.lstrip("/"))
    if not database or "/" in database:
        raise ValueError("DATABASE_URL must name one existing dedicated application database.")
    origin = urlsplit(env.get("MB_SITE_URL", ""))
    if (not origin.hostname or origin.username or origin.password or origin.query or origin.fragment
            or origin.path not in ("", "/") or origin.scheme != ("http" if local else "https")):
        raise ValueError("MB_SITE_URL must be the public HTTPS origin (HTTP only in local development).")
    if local and origin.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Local development requires a localhost site URL.")
    try:
        key = base64.b64decode(env.get("MB_ENCRYPTION_SECRET_KEY", ""), validate=True)
    except ValueError:
        key = b""
    if len(key) != 32:
        raise ValueError("MB_ENCRYPTION_SECRET_KEY must encode 32 random bytes as base64; preserve it across restarts.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", env.get("ADMIN_EMAIL", "")):
        raise ValueError("Set ADMIN_EMAIL to a valid email address.")
    password = env.get("ADMIN_PASSWORD", "")
    if len(password) < 16 or not all((re.search(r"[a-z]", password), re.search(r"[A-Z]", password), re.search(r"[0-9]", password))):
        raise ValueError("ADMIN_PASSWORD must be at least 16 characters with lowercase, uppercase and digits.")
    if not local and not env.get("PG_CA_CERT_BASE64"):
        raise ValueError("PG_CA_CERT_BASE64 is required for verified PostgreSQL TLS.")
    host = uri.hostname
    if ":" in host:
        host = f"[{host}]"
    options = {"sslmode": "disable" if local else "verify-full", "connectTimeout": "10"}
    if not local:
        options["sslrootcert"] = ca_path
    # Ignore URI query options so they cannot weaken certificate verification.
    jdbc = f"jdbc:postgresql://{host}:{uri.port or 5432}/{quote(database, safe='')}?{urlencode(options)}"
    java_env = {k: v for k, v in env.items() if not k.startswith("MB_DB_")}
    java_env.update(MB_DB_TYPE="postgres", MB_DB_CONNECTION_URI=jdbc,
                    MB_DB_USER=unquote(uri.username), MB_DB_PASS=unquote(uri.password),
                    MB_JETTY_HOST="127.0.0.1", MB_JETTY_PORT="3000",
                    MB_ANON_TRACKING_ENABLED="false")
    java_env.setdefault("JAVA_OPTS", "-XX:MaxRAMPercentage=60 -XX:+ExitOnOutOfMemoryError")
    for key in ("DATABASE_URL", "PG_CA_CERT_BASE64", "ADMIN_EMAIL", "ADMIN_PASSWORD"):
        java_env.pop(key, None)
    return java_env


def write_ca(encoded, path="/tmp/metabase-ca.pem"):
    pem = base64.b64decode(encoded, validate=True).decode("ascii")
    ssl.create_default_context(cadata=pem)
    target = Path(path)
    target.write_text(pem)
    target.chmod(0o600)


def api(path, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    request = Request("http://127.0.0.1:3000" + path, data=body,
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def ensure_admin(env, call=api):
    properties = call("/api/session/properties")
    if properties.get("has-user-setup") is True:
        return  # Existing users/passwords are never reset.
    token = properties.get("setup-token")
    if not token:
        raise RuntimeError("Cannot determine initial setup state; keeping public port closed.")
    call("/api/setup", {"token": token,
         "user": {"email": env["ADMIN_EMAIL"], "password": env["ADMIN_PASSWORD"],
                  "first_name": "Demo", "last_name": "Admin"},
         "prefs": {"site_name": "Metabase starter", "site_locale": "en"}})
    # Never publish until the server confirms that first-user setup is complete.
    if call("/api/session/properties").get("has-user-setup") is not True:
        raise RuntimeError("Initial setup did not complete; keeping public port closed.")


def main():
    env = dict(os.environ)
    java_env = configuration(env)
    if env.get("LOCAL_DEVELOPMENT") != "true":
        write_ca(env["PG_CA_CERT_BASE64"])
    children = []
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True
        for child in children:
            if child.poll() is None:
                child.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        metabase = subprocess.Popen(["/app/run_metabase.sh"], env=java_env)
        children.append(metabase)
        deadline = time.monotonic() + 600
        while not stopping:
            if metabase.poll() is not None:
                raise RuntimeError("Metabase exited before becoming ready.")
            try:
                healthy = api("/api/health").get("status") == "ok"
            except Exception:
                healthy = False
            if healthy:
                break
            if time.monotonic() > deadline:
                raise RuntimeError("Metabase startup exceeded ten minutes.")
            time.sleep(2)
        if stopping:
            return
        ensure_admin(env)
        if stopping:
            return
        proxy = subprocess.Popen(["nginx", "-c", "/app/nginx.conf", "-g", "daemon off;"])
        children.append(proxy)
        print("Metabase setup complete; public port 8080 is open.", flush=True)
        while not stopping:
            if any(child.poll() is not None for child in children):
                raise RuntimeError("A required process exited.")
            time.sleep(1)
    finally:
        stop(None, None)
        deadline = time.monotonic() + 30
        for child in children:
            try:
                child.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Driver/API responses can contain tokens or credentials; never print them.
        print(f"Startup failed ({type(exc).__name__}). Check required variables, PostgreSQL access and Metabase logs.", flush=True)
        raise SystemExit(1)
