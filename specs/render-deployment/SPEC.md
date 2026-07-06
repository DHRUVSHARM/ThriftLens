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
- Runtime config must support explicit local URLs and Render private host/port derivation for MCP services and MinIO.
- Database config must accept Render's `postgresql://` connection string and convert it to SQLAlchemy's asyncpg URL.
- App storage must create the MinIO bucket idempotently so Render does not need the local `minio-init` service.
- README, `.env.example`, and APPROACH notes must describe Render deployment knobs and post-create URL wiring.

## Non-Functional Requirements

- Keep deployment changes small and reversible.
- Do not introduce new runtime dependencies.
- Avoid logging secrets or secret-bearing URLs.
- Keep local Compose commands working.
- Keep Render private service ports away from private-network restricted ports.

## Acceptance Criteria

- `render.yaml` exists and describes the chosen Render service architecture.
- Frontend Dockerfile builds the app and starts with `next start`.
- Backend config exposes derived endpoints for Render MCP/MinIO host+port values.
- Existing MCP clients use the derived endpoint helpers.
- Database engine uses an asyncpg-compatible URL even when Render provides `postgresql://`.
- Upload and health paths can ensure the MinIO bucket exists without `minio-init`.
- `.env.example` documents Render host/port deployment variables with safe placeholders.
- README and APPROACH include Render deployment guidance.
- Automated tests cover config derivation and MinIO bucket creation behavior.

## Error Cases

- Missing Render public URLs should be documented as a two-pass setup issue for `NEXT_PUBLIC_API_BASE_URL` and `CORS_ALLOWED_ORIGINS`.
- Missing provider keys should remain surfaced by the existing health endpoint.
- MinIO unavailable should keep health returning a failed MinIO check instead of crashing the API process.
- Render Postgres URL format should not break SQLAlchemy async engine creation.

## Out Of Scope

- Full AWS deployment.
- Replacing MinIO with managed S3-compatible object storage.
- Horizontal autoscaling policy tuning.
- External monitoring/log streaming setup.
- Running the actual Render deployment from this local environment.
