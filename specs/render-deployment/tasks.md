# Render Deployment Tasks

- [x] Create Render deployment specification.
- [x] Add Render Blueprint for public, private, worker, datastore, and object-storage services.
- [x] Make frontend Docker image production-ready.
- [x] Add Render-aware config derivation for MCP services, MinIO, and Postgres URLs.
- [x] Remove Render dependency on `minio-init` through idempotent bucket creation.
- [x] Use lightweight `/api/live` liveness for Render health checks while keeping `/api/health` for dependency diagnostics.
- [x] Add search-specific SerpAPI timeout for slow live shopping responses.
- [x] Add automated tests for deployment config/storage mechanics.
- [x] Update `.env.example`, README, and APPROACH deployment notes.
- [x] Run relevant tests/build checks.
- [x] Add review report.
