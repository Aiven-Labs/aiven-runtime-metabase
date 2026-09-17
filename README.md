# Metabase starter for Aiven Runtime

Self-hosted **Metabase Open Source 0.63.18** with **Aiven for PostgreSQL** for durable application data. A generic demo starter: use Metabase's built-in Sample Database to explore, or connect your own data sources after signing in.

## Design

```text
Browser --HTTPS--> Aiven Runtime ingress --> :8080 nginx
                                                    |
                                         127.0.0.1:3000 Metabase
                                                    |
                                             verified TLS
                                                    |
                                         Aiven PostgreSQL
                                         (application data)
```

The application database stores users, questions, dashboards, settings, and saved data-source credentials. It is **different from the databases you connect for analytics**. Give this starter its own PostgreSQL service/database; do not point it at a Temporal database or a business data warehouse.

The wrapper validates configuration, starts Metabase on loopback, waits for migrations, and uses its setup API to create the first admin. Only after Metabase confirms setup is complete does nginx open port 8080. Existing users and passwords are never reset on restart. This prevents an unfinished first-run setup page from being exposed publicly.

Metabase provides the login screen. No extra shared-password page or browser Basic authentication is used. Both processes run as a non-root user; the wrapper forwards shutdown signals and exits if either required process stops.

## Run locally

Requires Docker Compose v2 and a running container engine.

1. Copy `.env.example` to `.env`.
2. Set `POSTGRES_PASSWORD` to a URL-safe random value (e.g. `openssl rand -hex 24`), `ADMIN_EMAIL` to your chosen admin login, and `ADMIN_PASSWORD` to a unique password of at least 16 characters containing lowercase, uppercase, and digits. If you use special characters in the PostgreSQL password, URL-encode them in the Compose connection URI.
3. Generate `MB_ENCRYPTION_SECRET_KEY` once with `openssl rand -base64 32`. Keep this key and back it up separately from the database.
4. Run `docker compose up --build -d`. First startup can take several minutes while migrations run.
5. Open <http://localhost:8080> and sign in with your admin email/password.

Local Compose publishes only on loopback and explicitly disables PostgreSQL TLS inside its private Docker network. Never set `LOCAL_DEVELOPMENT=true` on Runtime.

`docker compose down` preserves the application database. `docker compose down -v` **permanently deletes local users, questions, dashboards, and settings**.

## Deploy on Aiven Runtime

1. Review, commit, and push this repo to GitHub. Staged local files are not available to Runtime.
2. In your Aiven project, choose **Runtime > Deploy application**, select this repository and branch, and scan **compose.aiven.yaml**. The root Dockerfile can also be deployed using Aiven MCP/API with an `application_service_credential` PostgreSQL integration mapping the connection string to `DATABASE_URL`.
3. Choose a dedicated PostgreSQL service. PostgreSQL 16 is the reference version. The existing database named in the connection URI (typically `defaultdb`) must be empty initially and owned by the supplied account. Metabase creates/migrates its tables; it does not create the database itself.
4. Start with **one Runtime replica and 2 GiB RAM** as a demo estimate. Java uses a maximum heap of 60% of the container memory by default. Check available internal/free plans and displayed prices before creating either resource. This is not a tested minimum or a production sizing recommendation.
5. Configure the variables below. Keep credentials and the encryption key in Runtime secrets, outside Git.
6. Publish **only HTTP port 8080**. The upstream image also advertises port 3000, but this template binds it to loopback for private setup. Do not add a public route to it.
7. Set `MB_SITE_URL` to the generated HTTPS origin. If Runtime creates the app before its hostname is known, let the initial attempt fail closed, then set the variable and redeploy.
8. Wait for migrations and the log message `Metabase setup complete; starting public proxy on port 8080.` Confirm `/api/health` returns HTTP 200, then sign in with the configured admin credentials.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL URI injected by the service integration, including URL-encoded credentials, database name, and actual Aiven port |
| `PG_CA_CERT_BASE64` | Aiven project CA certificate encoded as one line |
| `ADMIN_EMAIL` | First admin's login email; required by this wrapper on every startup |
| `ADMIN_PASSWORD` | First admin password: at least 16 characters with lowercase, uppercase, and digits; required on every startup |
| `MB_ENCRYPTION_SECRET_KEY` | Base64-encoded 32-byte random key from `openssl rand -base64 32`; preserve across restarts, redeploys, and restores |
| `MB_SITE_URL` | Exact public HTTPS origin, e.g. `https://your-app.eur-1.aiven.app` |
| `JAVA_OPTS` | Optional JVM tuning; default `-XX:MaxRAMPercentage=60 -XX:+ExitOnOutOfMemoryError` |

Encode the project CA using `openssl base64 -A -in ca.pem`. Runtime values cannot contain literal newlines. The wrapper decodes the PEM and requires PostgreSQL certificate **and hostname** verification (`sslmode=verify-full`). URI query options cannot override TLS settings. The database username/password are passed separately from the JDBC URI to preserve special characters.

Changing `ADMIN_EMAIL` or `ADMIN_PASSWORD` after setup **does not** change the existing account. Use Metabase's account management to change credentials. No email/SMTP service is configured by this template, so password-reset email delivery needs separate setup.

Do not replace the encryption key on an existing installation: previously stored database credentials may become unreadable. Back up PostgreSQL and this key before upgrades. Follow Metabase's supported upgrade process; do not downgrade a migrated database.

## Try the starter

After signing in, explore Metabase's built-in Sample Database, create a question, and save it in a collection or dashboard. Restart/redeploy the app and confirm the saved content and login still exist. Sample data is bundled demo content; durable application state lives in PostgreSQL.

To connect real data, use **Admin > Databases** and a separate least-privilege analytics account. Do not add the internal Metabase application database as an analytics source. Configure verified TLS for each new data source; the application-database TLS setup does not automatically configure analytics connections.

## Validation and limitations

Run wrapper tests with Python 3.10 or newer:

```sh
python3 -m unittest discover -s tests -v
```

See [VALIDATION.md](VALIDATION.md) for completed tests and remaining live checks. The local Docker health check uses `/api/health`; Runtime's OCI builder may ignore Dockerfile HEALTHCHECK, so also check service status, browser login, and persistence.

This is a single-replica demo, without HA, load testing, SMTP, SSO configuration, or a production access model. Use synthetic data for initial testing. Metabase's built-in permissions and session throttling remain enabled. Anonymous usage tracking is disabled. The setup API used by the wrapper is version-sensitive and must be checked when upgrading the pinned Metabase image.

## References

- [Metabase Docker deployment](https://www.metabase.com/docs/latest/installation-and-operation/running-metabase-on-docker)
- [Metabase application database](https://www.metabase.com/docs/latest/installation-and-operation/configuring-application-database)
- [Metabase environment variables](https://www.metabase.com/docs/latest/configuring-metabase/environment-variables)
- [Metabase 0.63.18 release](https://github.com/metabase/metabase/releases/tag/v0.63.18)
- [Aiven Runtime deployment](https://aiven.io/docs/products/runtime/deploy-apps)
- [Aiven Runtime Compose manifests](https://aiven.io/docs/products/runtime/manifest-files/compose-files)
