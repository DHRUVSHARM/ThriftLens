# Render Deployment Spec

## Objective

Make ThriftLens deployable on Render with a production-shaped service split while preserving the local Docker Compose review path.

## Context

ThriftLens currently runs locally through Docker Compose with public frontend/API containers, private MCP-style backend services, Celery worker/beat, Postgres, Redis, and MinIO. The deployment target is Render using a root `render.yaml` Blueprint.

Render official docs support Blueprint-managed services, Docker services, private services, background workers, Key Value, Postgres, and persistent disks. Private services and web services can be reached over Render's private network; background workers can send private-network requests but cannot receive them.

## Business Rules

- Only the frontend and API should be public.
- MCP services and MinIO should be private Render services.
- The API and worker should continue using Postgres for durable job state and Redis-compatible queueing for Celery.
- The Celery worker must run with bounded concurrency on Render Starter so the AI/MCP stack does not fan out into the default CPU-count prefork pool.
- Uploaded images should remain in private S3-compatible storage with the existing TTL cleanup behavior.
- Local Docker Compose must remain the fallback review path.
- Real provider secrets must not be committed.

## Functional Requirements

- Add a root `render.yaml` Blueprint defining:
  - frontend web service
  - FastAPI web service
  - Celery worker
  - Celery Beat worker
  - extraction, discovery, and ranking private services
  - private MinIO service with persistent disk
  - Render Key Value instance
  - Render Postgres database
- Frontend Docker image must build and run production Next.js instead of `next dev`.
- Backend web startup must support Render's runtime `PORT`.
- MinIO must run from a repo-owned Dockerfile so Render uses a predictable container `CMD`.
- Runtime config must support explicit local URLs and Render private host/port derivation for MCP services and MinIO.
- Database config must accept Render's `postgresql://` connection string and convert it to SQLAlchemy's asyncpg URL.
- App storage must create the MinIO bucket idempotently so Render does not need the local `minio-init` service.
- Worker commands must pin Celery concurrency/prefetch and recycle child processes to keep memory predictable on small instances.
- Live SerpAPI search must use a source-specific timeout so slow Google Shopping results do not force a failed job while generic model/provider calls stay tightly bounded.
- Render's API web-service HTTP health check must use a cheap liveness endpoint (`/api/live`) instead of the full dependency health endpoint.
- The full runtime health endpoint (`/api/health`) must remain available for the frontend startup check, manual smoke tests, and dependency diagnostics.
- README, `.env.example`, and APPROACH notes must describe Render deployment knobs and post-create URL wiring.
- `CORS_ALLOWED_ORIGINS` should be committed in `render.yaml` once the stable public frontend URL is known, because it is not secret and should not be missed during Blueprint sync.

## Non-Functional Requirements

- Keep deployment changes small and reversible.
- Do not introduce new runtime dependencies.
- Avoid logging secrets or secret-bearing URLs.
- Keep local Compose commands working.
- Prefer queue backpressure over high per-worker parallelism for the Starter deployment.
- Keep Render private service ports away from private-network restricted ports.
- Keep platform liveness checks lightweight; deeper Postgres, Redis, MinIO, and provider-key checks should be explicit runtime diagnostics rather than Render's every-few-seconds probe.
- Keep `SERPAPI_TIMEOUT_SECONDS` separate from `PROVIDER_TIMEOUT_SECONDS` so live search latency does not make all model calls wait longer.
- Do not enable Render Preview Environments because the chosen Hobby workspace does not support them.

## Acceptance Criteria

- `render.yaml` exists and describes the chosen Render service architecture.
- Frontend Dockerfile builds the app and starts with `next start`.
- Backend config exposes derived endpoints for Render MCP/MinIO host+port values.
- Existing MCP clients use the derived endpoint helpers.
- Database engine uses an asyncpg-compatible URL even when Render provides `postgresql://`.
- Upload and health paths can ensure the MinIO bucket exists without `minio-init`.
- API exposes `/api/live` for Render liveness and keeps `/api/health` for full dependency health.
- Render Blueprint documents and sets `SERPAPI_TIMEOUT_SECONDS` separately from the generic provider timeout.
- Render and Docker Compose worker commands set bounded Celery concurrency and prefetch behavior.
- `.env.example` documents Render host/port deployment variables with safe placeholders.
- README and APPROACH include Render deployment guidance.
- Automated tests cover config derivation and MinIO bucket creation behavior.

## Error Cases

- Missing Render public API URL should be documented as a two-pass setup issue for `NEXT_PUBLIC_API_BASE_URL`; CORS should include the stable deployed frontend origin plus local development origins in `render.yaml`.
- Missing provider keys should remain surfaced by the existing health endpoint.
- MinIO unavailable should keep health returning a failed MinIO check instead of crashing the API process.
- `/api/live` should remain dependency-light so transient Redis/Postgres/MinIO issues do not cause Render to restart an otherwise reachable API process.
- Render Postgres URL format should not break SQLAlchemy async engine creation.

## Out Of Scope

- Full AWS deployment.
- Replacing MinIO with managed S3-compatible object storage.
- Horizontal autoscaling policy tuning.
- Render Preview Environments.
- External monitoring/log streaming setup.
- Running the actual Render deployment from this local environment.
