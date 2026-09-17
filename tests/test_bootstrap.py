import base64
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from bootstrap import configuration, ensure_admin, write_ca


def settings():
    return {
        "DATABASE_URL": "postgresql://demo:p%40ss%26word@db.example.com:1234/defaultdb?sslmode=disable",
        "PG_CA_CERT_BASE64": "provided-at-runtime",
        "MB_SITE_URL": "https://metabase.example.com",
        "MB_ENCRYPTION_SECRET_KEY": base64.b64encode(b"x" * 32).decode(),
        "ADMIN_EMAIL": "admin@example.com",
        "ADMIN_PASSWORD": "Test-Password-123456",
    }


class BootstrapTests(unittest.TestCase):
    def test_credentials_and_tls(self):
        env = configuration(settings())
        self.assertEqual(env["MB_DB_PASS"], "p@ss&word")
        self.assertNotIn("p@ss", env["MB_DB_CONNECTION_URI"])
        self.assertIn("sslmode=verify-full", env["MB_DB_CONNECTION_URI"])
        self.assertEqual(env["MB_JETTY_HOST"], "127.0.0.1")
        self.assertNotIn("ADMIN_PASSWORD", env)

    def test_inherited_db_settings_cannot_override_connection(self):
        given = settings() | {"MB_DB_TYPE": "h2", "MB_DB_PASS": "wrong", "MB_DB_CONNECTION_URI_FILE": "/secret"}
        env = configuration(given)
        self.assertEqual(env["MB_DB_TYPE"], "postgres")
        self.assertEqual(env["MB_DB_PASS"], "p@ss&word")
        self.assertNotIn("MB_DB_CONNECTION_URI_FILE", env)

    def test_required_settings(self):
        for key in ("DATABASE_URL", "PG_CA_CERT_BASE64", "MB_SITE_URL", "MB_ENCRYPTION_SECRET_KEY", "ADMIN_EMAIL", "ADMIN_PASSWORD"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                configuration(settings() | {key: ""})

    def test_http_requires_explicit_local_mode(self):
        with self.assertRaises(ValueError):
            configuration(settings() | {"MB_SITE_URL": "http://example.com"})
        env = configuration(settings() | {"LOCAL_DEVELOPMENT": "true", "MB_SITE_URL": "http://localhost:8080", "PG_CA_CERT_BASE64": ""})
        self.assertIn("sslmode=disable", env["MB_DB_CONNECTION_URI"])
        with self.assertRaises(ValueError):
            configuration(settings() | {"LOCAL_DEVELOPMENT": "true", "MB_SITE_URL": "http://example.com"})

    def test_ipv6_and_encoded_database_name(self):
        env = configuration(settings() | {"DATABASE_URL": "postgres://demo:pass@[::1]:5432/demo%20db"})
        self.assertIn("[::1]:5432/demo%20db?", env["MB_DB_CONNECTION_URI"])

    def test_invalid_ca_rejected_without_writing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ca.pem"
            with self.assertRaises(Exception):
                write_ca(base64.b64encode(b"not a certificate").decode(), str(path))
            self.assertFalse(path.exists())

    def test_existing_user_is_never_reset(self):
        call = Mock(return_value={"has-user-setup": True})
        ensure_admin(settings(), call)
        call.assert_called_once_with("/api/session/properties")

    def test_new_admin_uses_setup_token_and_requires_confirmation(self):
        call = Mock(side_effect=[{"has-user-setup": False, "setup-token": "test-token"}, {"id": "session"}, {"has-user-setup": True}])
        ensure_admin(settings(), call)
        path, payload = call.call_args_list[1].args
        self.assertEqual(path, "/api/setup")
        self.assertEqual(payload["token"], "test-token")
        self.assertEqual(payload["user"]["email"], "admin@example.com")
        self.assertEqual(call.call_count, 3)

    def test_uncertain_setup_remains_closed(self):
        for responses in ([{}], [{"setup-token": "token"}, {}, {"has-user-setup": False}]):
            with self.subTest(responses=responses), self.assertRaises(RuntimeError):
                ensure_admin(settings(), Mock(side_effect=responses))


if __name__ == "__main__":
    unittest.main()
