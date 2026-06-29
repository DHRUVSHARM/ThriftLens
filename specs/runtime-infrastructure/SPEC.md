# Runtime Infrastructure Spec

Status: Draft for implementation review

Sources:
- `specs/product-prd/PRD.md`
- `specs/technical-design/TECHNICAL_DESIGN.md`

## Objective

Provide the runtime foundation for ThriftLens so the app can run from a fresh Linux container with production-shaped services: frontend, FastAPI gateway, Celery worker, Postgres, Redis, and MinIO.

## Context

ThriftLens uses asynchronous product research jobs. The web gateway must stay responsive while workers run AI extraction and source-backed research. Durable state belongs in Postgres, accepted task execution belongs in Celery/Redis, and uploaded image blobs belong in MinIO.

## Business Rules

- The app must run through Docker Compose for reviewer setup.
- The frontend uses Next.js App Router, React, TypeScript, Tailwind CSS, shadcn/ui primitives, and `lucide-react`.
- Redis is used for Celery broker/cache behavior, not durable product state.
- Postgres is the durable source of truth for job status, product references, research briefs, source attempts, and safe errors.
- MinIO stores temporary uploaded image bytes only.
- Provider mode must be server-side configuration: `REAL_MODE`, `SAMPLE_MODE`, or `TEST_MODE`.
- Secrets must never be committed, logged, or exposed to the browser.

## Functional Requirements

- Provide Docker Compose services for:
  - frontend
  - api
  - worker
  - postgres
  - redis
  - minio
- Provide documented environment variables in `.env.example`:
  - `PROVIDER_MODE`
  - `NEXT_PUBLIC_API_BASE_URL`
  - `DATABASE_URL`
  - `REDIS_URL`
  - `GEMINI_API_KEY`
  - `SERPAPI_API_KEY`
  - `SERPAPI_MCP_BASE_URL`
  - `MINIO_ENDPOINT`
  - `MINIO_ACCESS_KEY`
  - `MINIO_SECRET_KEY`
  - `MINIO_BUCKET`
  - `OBJECT_STORAGE_FORCE_PATH_STYLE`
  - `MAX_QUEUED_JOBS`
  - `MAX_ACTIVE_JOBS`
  - `MAX_UPLOAD_MB`
  - `MAX_TEXT_LENGTH`
  - `LIVE_PROVIDER_SMOKE`
- Initialize or document creation of the MinIO bucket used for temporary image storage.
- Provide database migration support for the required tables:
  - `research_jobs`
  - `job_attempts`
  - `dependency_health`
  - `uploaded_images`
- Persist structured artifacts as JSON/JSONB where appropriate:
  - `ProductReference`
  - `ProductResearchBrief`
  - `ResearchSourceResult`
  - provider attempt metadata
- Provide health checks for API, worker dependencies, Postgres, Redis, and MinIO where practical.

## Non-Functional Requirements

- Fresh setup should not require undeclared global services.
- Services should be independently restartable.
- Job state should survive browser refreshes and worker restarts.
- Object storage credentials must be server-side only.
- MinIO should be treated as production-feasible when deployed with persistent storage, backups, health checks, and cleanup.

## Acceptance Criteria

- `docker compose up` starts the app services documented for V1.
- API can connect to Postgres, Redis, and MinIO using environment configuration.
- Worker can connect to Postgres, Redis, MinIO, Gemini configuration, and SerpAPI configuration.
- `.env.example` contains every required variable with safe placeholder values.
- Postgres tables can store job status, provider mode, product reference JSON, partial/final brief JSON, attempts, dependency health, and uploaded image metadata.
- Redis is not used as the source of truth for user-visible research results.
- MinIO stores raw images; Postgres stores only image metadata.
- Missing required infrastructure in `REAL_MODE` produces explicit configuration/unavailable errors.

## Error Cases

- Postgres unavailable: API returns service unavailable for job creation/status.
- Redis unavailable: API returns service unavailable before pretending a job was queued.
- MinIO unavailable during image upload: job is not accepted and the user sees a recoverable upload/storage error.
- Missing `GEMINI_API_KEY` or `SERPAPI_API_KEY` in `REAL_MODE`: job is rejected or fails with explicit provider configuration error.

## Out of Scope

- Managed cloud object storage setup.
- Multi-region deployment.
- User accounts, authentication, or long-term saved history.
- Production observability stack beyond basic logs/health checks.
