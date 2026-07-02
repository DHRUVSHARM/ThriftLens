# Backend Gateway Review

Status: Approved for next slice

## Spec Compliance

- Pass: `POST /api/research-jobs`, `GET /api/research-jobs/{job_id}`, and `POST /api/research-jobs/{job_id}/retry` are implemented under the FastAPI gateway.
- Pass: Gateway handlers stay thin and delegate validation, persistence, object storage, queue enqueueing, and response mapping to gateway/repository/storage modules.
- Pass: Text input is treated as untrusted data and validated before persistence or queue enqueueing.
- Pass: Image input validates MIME type, non-empty bytes, and upload size before MinIO upload.
- Pass: Valid image jobs upload raw bytes to MinIO and store metadata in `uploaded_images`.
- Pass: Job state is durable in Postgres; Redis is used only through Celery enqueueing.
- Pass: `REAL_MODE` missing provider keys return an explicit configuration error.
- Pass: `SAMPLE_MODE` does not require live provider keys and produces visibly sample/static final brief labeling through the minimal worker task.
- Pass: Gateway responses expose safe job state only: `jobId`, status, progress, retryability, provider mode, safe error, partial brief, and final brief.
- Pass: Browser CORS preflight from the configured local frontend origin succeeds without allowing arbitrary origins.

## Acceptance Criteria Coverage

- Valid text job returns `jobId` and `queued`: covered by `test_create_text_job_returns_queued_and_can_be_polled`.
- Valid image job uploads image and stores metadata: covered by `test_create_image_job_stores_metadata_and_can_be_polled`.
- Empty input rejected before queue/provider calls: covered by `test_empty_text_input_is_rejected`.
- Unsupported and oversized images rejected: covered by `test_unsupported_image_type_is_rejected` and `test_oversized_image_is_rejected`.
- Missing provider keys in `REAL_MODE`: covered by `test_real_mode_missing_provider_keys_is_explicit`.
- `SAMPLE_MODE` succeeds without keys and labels sample/static output: covered by `test_sample_mode_job_eventually_gets_static_final_brief`.
- Polling returns safe state: covered by text and image polling tests.
- Retry refuses non-retryable jobs: covered by `test_retry_refuses_non_retryable_job`.
- Browser CORS preflight succeeds for job creation: covered by `test_browser_preflight_allows_configured_frontend_origin`.

## Identified Gaps

- No blocking backend gateway gaps.
- Retryable-job enqueueing exists, but there is not yet a natural retryable workflow failure until worker/provider slices add real failure states.
- Expired job behavior is specified but not yet meaningful because no cleanup/expiration path exists in V1 gateway behavior.

## Improvement Suggestions

- Add repository-level tests around retryable failure state once worker/provider failures are implemented.
- Add a small integration check for queued/active load shedding when worker orchestration creates longer-running jobs.
- Keep endpoint tests async so the production-style SQLAlchemy async pool is exercised without `TestClient` event-loop churn.
- Keep Celery worker async work on the persistent worker loop runner while worker tasks remain synchronous Celery entrypoints.

## Verification Commands

- `python3 -m py_compile backend/app/config.py backend/app/db.py backend/app/storage.py backend/app/redis_client.py backend/app/health.py backend/app/async_runtime.py backend/app/schemas.py backend/app/job_repository.py backend/app/object_storage.py backend/app/gateway.py backend/app/routes.py backend/app/main.py backend/app/worker.py`
- `docker compose exec api python -m pytest tests/test_backend_gateway.py`
- `curl -i -X OPTIONS http://localhost:8000/api/research-jobs -H Origin:http://localhost:3000 -H Access-Control-Request-Method:POST -H Access-Control-Request-Headers:content-type`
- `docker compose exec api python -m pytest tests`
- `python3 -m unittest backend.tests.test_runtime_infrastructure_static`
