# Validation

Checked on 2026-09-17.

## Passed

- Nine Python unit tests: URI credential decoding, mandatory configuration, enforced TLS, isolation from conflicting database environment variables, explicit local-only mode, IPv6/database-name encoding, invalid CA rejection, existing-user preservation, first-admin setup and confirmation, and failure when setup state is uncertain.
- Official Metabase release verified as 0.63.18, with Docker tag `metabase/metabase:v0.63.18.x` available for amd64 and arm64.
- Wrapper behavior checked against the official release's Docker entrypoint and `/api/setup` implementation.

## First Aiven Runtime attempt

Deployed commit `776c2cb63c00ae4e3e77b5f52ca67015ebef5934` through Aiven MCP in `cara-test`, AWS Dublin, using `startup-100-2048` Runtime and dedicated `startup-4` PostgreSQL 16.

- Container build passed. Runtime ignores the OCI Dockerfile HEALTHCHECK.
- Metabase connected to PostgreSQL with the wrapper's verified TLS configuration and initialized its schema.
- Saved-credential encryption was enabled, and the private `/api/setup` call returned HTTP 200. The wrapper confirmed first-user setup completion.
- Public access failed: nginx attempted to create its default FastCGI temporary directory under `/var/lib/nginx`, which the non-root user cannot write.
- Staged correction places all nginx temporary paths under `/tmp`, sets a writable prefix and stderr logging, and validates nginx before starting Metabase.
- Nine unit tests still pass. The corrected container must be built and deployed before the proxy fix can be marked verified.
- The initial admin remains in PostgreSQL; it must not be reset during the retry.

## Pending after the corrective commit/push

- Linux container build and nginx configuration check.
- Confirm existing-admin startup succeeds after the proxy correction.
- Runtime public login and authenticated UI, plus a saved question/dashboard.
- Application restart and persistence of users and saved content.
- Runtime resource sizing beyond the initial 2 GiB estimate.
- Console scanning of `compose.aiven.yaml` and local Docker Compose execution.

No local Docker engine is available. Passing unit tests does not establish that the full container deployment works. Test services were created for the live attempt; prior Temporal and Streamlit services were unchanged.
