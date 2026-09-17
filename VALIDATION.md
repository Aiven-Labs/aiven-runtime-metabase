# Validation

Validated on 2026-09-17. Live application commit: `977555e054e54d944012b84c9bdbf92283f80e66`.

## Passed locally

- Nine Python unit tests cover configuration, encoded credentials, enforced TLS, conflicting database environment settings, explicit local mode, invalid CA rejection, first-admin setup and confirmation, and preservation of existing accounts.
- Official Metabase 0.63.18 image and its amd64/arm64 manifest digest were verified.

## Passed on Aiven Runtime

Deployed through Aiven MCP using the root Dockerfile, in project `cara-test`, cloud `aws-eu-west-1`:

- `metabase-demo`: Runtime `startup-100-2048` (2 GiB RAM).
- `metabase-postgres`: dedicated PostgreSQL 16 `startup-4`.
- Both services from the failed attempt were deleted before this clean deployment. Existing Temporal and Streamlit services were unchanged.
- Corrected container build and non-root nginx configuration validation passed. The original nginx temporary-directory permission failure is resolved.
- Metabase initialized its schema over the wrapper's `verify-full` PostgreSQL connection and enabled saved-credential encryption.
- First-admin setup completed on loopback before the public proxy started. Public session properties report setup complete and no setup token.
- Public `/api/health` returns HTTP 200 with status `ok`. An anonymous `/api/user/current` request returns HTTP 401.
- Generated admin credentials work through both the API and native browser login screen.
- Built-in Sample Database analysis rendered charts and reported 200 products. Saved the analysis as dashboard `A look at Products` (ID 3, 11 cards).
- Created a separate synthetic `Runtime persistence check` dashboard (ID 2).
- Powered the Runtime application off, then back on while PostgreSQL remained running. After rebuild/startup, the same admin login works and both dashboards remain available; first-admin setup stays closed.
- Final Runtime build status SUCCESS, deployment COMPLETED, service RUNNING.

The services remain running at observed rates of $0.06849/hour for Runtime and $0.151/hour for PostgreSQL: $0.21949/hour, approximately $5.27/day combined. Other project services are separate.

## Limits

- This validates the root Dockerfile/MCP deployment path. Console scanning of `compose.aiven.yaml` and local Docker Compose execution are not yet tested; no local Docker engine is available.
- Runtime ignores Dockerfile HEALTHCHECK for OCI images. Service status, public health, authentication, sample queries, and restart persistence were checked separately.
- No HA, multi-replica, load, backup/restore, SMTP, SSO, or external analytics-database tests were performed.
- The 2 GiB plan passed this small demo test; it is not a production sizing recommendation.
- Credentials and the application encryption key are stored privately outside Git.
