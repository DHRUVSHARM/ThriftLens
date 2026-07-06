# Render Deployment Review

## Spec Compliance

The implementation matches the Render deployment spec:

- Added `render.yaml` with public web/API services, private MCP services, worker/beat, private MinIO, Render Key Value, and Render Postgres.
- Bounded Celery worker concurrency/prefetch in Render and Docker Compose so Starter instances do not spawn the default CPU-count prefork pool.
- Made the frontend Docker image build and run production Next.js.
- Made the backend Docker image honor runtime `PORT`.
- Added a repo-owned MinIO Dockerfile to avoid Render image-command parsing ambiguity.
- Added Render host/port derivation for MCP services and MinIO while preserving explicit local URLs.
- Normalized Render Postgres `postgresql://` URLs to `postgresql+asyncpg://` for SQLAlchemy async engine creation.
- Added idempotent MinIO bucket creation in the app storage boundary.
- Added `/api/live` as the Render health-check target so platform probes do not run the full dependency health check every few seconds.
- Added `SERPAPI_TIMEOUT_SECONDS` so slow Google Shopping responses have a longer bounded search budget than generic model/provider calls.
- Updated `.env.example`, README, and APPROACH with deployment variables and Render wiring notes.

## Acceptance Criteria Coverage

- `render.yaml` architecture: covered by static test in `test_runtime_infrastructure_static.py`.
- Production Dockerfiles: covered by frontend build and backend compile/test commands.
- Config derivation: covered by `test_render_deployment_config.py`.
- MinIO bucket creation: covered by `test_render_deployment_config.py`.
- Bounded worker concurrency: covered by static deployment checks in `test_runtime_infrastructure_static.py`.
- Lightweight API liveness: covered by `test_backend_gateway.py` and static `render.yaml` checks.
- SerpAPI-specific timeout: covered by `test_discovery_mcp_tools.py`.
- Environment/docs coverage: covered by static env-var documentation test and manual review of README/APPROACH.

## Identified Gaps

- Actual Render deployment URL is still `TBD` until the Blueprint is created and verified in the Render dashboard.
- Render Blueprint validation was not run through Render CLI/API locally.
- Render Preview Environments are intentionally disabled because the selected Hobby workspace does not support them.

## Improvement Suggestions

- After deployment, confirm Render probes `/api/live`, smoke test `/api/health`, one text job, one image/camera job, and one image cleanup cycle.
- If the app gets real traffic, replace private MinIO with managed S3-compatible object storage and add external log/metrics streaming.
