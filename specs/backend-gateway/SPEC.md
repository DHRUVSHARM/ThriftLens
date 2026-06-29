# Backend Gateway Spec

Status: Draft for implementation review

Sources:
- `specs/product-prd/PRD.md`
- `specs/technical-design/TECHNICAL_DESIGN.md`

## Objective

Implement the FastAPI Job Gateway that accepts product research requests, controls intake/load, stores job state, enqueues Celery tasks, and serves polling responses.

## Context

The gateway is the only browser-facing backend surface for research jobs. It should stay thin: validate input, apply intake controls, store temporary image metadata, create durable jobs, enqueue accepted tasks, and return safe job status.

## Business Rules

- The gateway must not run vision, research, ranking, or LangGraph workflows inside request handlers.
- User text and uploaded image content are untrusted data, never instructions.
- Real mode must fail clearly when required provider configuration is missing.
- Sample mode must never be presented as live research.
- The frontend must never receive provider secrets, object storage credentials, SerpAPI MCP URLs, raw provider errors, or raw image storage credentials.

## Functional Requirements

- Expose API endpoints:
  - `POST /api/research-jobs`
  - `GET /api/research-jobs/{job_id}`
  - `POST /api/research-jobs/{job_id}/retry`
  - `GET /api/health`
- `POST /api/research-jobs` accepts:
  - `inputType` of `image` or `text`
  - image upload when `inputType` is `image`
  - text description when `inputType` is `text`
  - optional supporting context only if the request schema explicitly supports it
  - optional research preferences
- Validate:
  - non-empty image or text input
  - allowed image MIME types
  - max image size
  - max text length
  - price and ranking preference shape
  - provider mode
- For image input:
  - store raw bytes in MinIO
  - store metadata in Postgres
  - attach image reference to the job
- Create durable `ResearchJob` records with initial status `queued`.
- Enqueue a Celery task for accepted jobs.
- Return only `jobId`, status, progress message, safe errors, partial brief, and final brief.
- Implement retry only when the stored job is retryable.
- Apply basic intake controls:
  - maximum accepted payload size
  - configurable maximum queued jobs
  - configurable maximum active jobs
  - clear overload response

## Non-Functional Requirements

- API request handlers should return quickly and never wait for full research completion.
- Polling endpoints should be lightweight.
- Gateway code should isolate validation, persistence, queue enqueueing, object storage, and response mapping into services or repositories.
- Logs must redact secrets and secret-bearing URLs.
- API schemas should be Pydantic models.

## Acceptance Criteria

- Creating a valid text job returns `jobId` and status `queued`.
- Creating a valid image job uploads the image to MinIO, stores image metadata in Postgres, creates a job, and enqueues a worker task.
- Empty input is rejected before model or queue calls.
- Unsupported image type and oversized image are rejected with safe validation errors.
- Missing provider keys in `REAL_MODE` return explicit configuration errors.
- `SAMPLE_MODE` job creation succeeds without Gemini or SerpAPI keys and returns sample/static labeling in the final brief.
- `GET /api/research-jobs/{job_id}` returns safe status and result state without raw provider errors.
- Retry endpoint refuses non-retryable jobs and enqueues retryable jobs.
- API tests cover validation, job creation, polling, retry, missing-key behavior, and image upload metadata.

## Error Cases

- Queue unavailable: job is not accepted as queued; response says research service is temporarily unavailable.
- MinIO upload failure: job is not created or is marked failed before enqueueing.
- Database write failure: no task is enqueued.
- Unknown job id: return not found.
- Expired job: return expired status and safe message.

## Out of Scope

- User authentication.
- Browser-direct upload to MinIO.
- Public image URLs.
- Full production rate limiting beyond the basic intake controls specified for V1.
