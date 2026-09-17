# Validation

Checked on 2026-09-17.

## Passed

- Nine Python unit tests: URI credential decoding, mandatory configuration, enforced TLS, isolation from conflicting database environment variables, explicit local-only mode, IPv6/database-name encoding, invalid CA rejection, existing-user preservation, first-admin setup and confirmation, and failure when setup state is uncertain.
- Official Metabase release verified as 0.63.18, with Docker tag `metabase/metabase:v0.63.18.x` available for amd64 and arm64.
- Wrapper behavior checked against the official release's Docker entrypoint and `/api/setup` implementation.

## Pending after the first user commit/push

- Linux container build and nginx configuration check.
- Aiven PostgreSQL TLS connection, schema migrations, and first-admin bootstrap.
- Runtime public login and authenticated UI, plus a saved question/dashboard.
- Application restart and persistence of users and saved content.
- Runtime resource sizing beyond the initial 2 GiB estimate.
- Console scanning of `compose.aiven.yaml` and local Docker Compose execution.

No local Docker engine is available. Passing unit tests does not establish that the full container deployment works. No Aiven services were created or changed for these checks.
