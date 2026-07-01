# Worker Orchestration Review

Status: Approved for next slice

## Spec Compliance

- Pass: Celery `process_research_job` now invokes a bounded `ResearchWorkflow` by `job_id`.
- Pass: The workflow loads durable job input, provider mode, preferences, and image metadata from Postgres.
- Pass: Fixed workflow stages are implemented in server code: extraction, validation/repair, research, source normalization, ranking, and brief assembly.
- Pass: Job state updates after major stages: `extracting_reference`, `researching_sources`, `ranking_results`, `complete`, `partial`, and `failed`.
- Pass: `ProductReference` is stored as the durable artifact after extraction.
- Pass: Research failure after extraction preserves `ProductReference` and stores a partial `ProductResearchBrief`.
- Pass: Deterministic ranking is the baseline and remains available when model-assisted ranking explanation fails.
- Pass: Provider attempts and dependency health updates are recorded without secrets.
- Pass: Celery sync tasks run async workflow code through a persistent worker-process event loop, preserving production-style DB pooling.

## Acceptance Criteria Coverage

- Queued sample-mode text job completes and stores final `ProductResearchBrief`: covered by `test_sample_mode_text_job_completes_with_final_brief`.
- Queued sample-mode image job completes and stores final `ProductResearchBrief`: covered by `test_sample_mode_image_job_completes_with_final_brief`.
- Invalid model output is repaired once, then fails safely if still invalid: covered by `test_invalid_extraction_output_is_repaired_once` and `test_invalid_extraction_output_fails_after_repair`.
- Research failure after extraction preserves `ProductReference`: covered by `test_research_failure_preserves_product_reference_as_partial`.
- Ranking model failure returns deterministic ranking: covered by `test_ranking_model_failure_uses_deterministic_fallback`.
- No verified match returns possible match guidance: covered by `test_no_verified_match_returns_possible_match_guidance`.
- Job state updates and polling-readable final state: covered by gateway polling tests and `test_job_state_and_attempts_are_updated_after_major_stages`.
- Attempt metadata recorded without secrets: covered by attempt count assertions and review of stored fields.

## Identified Gaps

- No blocking worker orchestration gaps for the sample/test workflow.
- Real Gemini and SerpAPI provider calls are intentionally deferred to provider integration specs.
- Raw image cleanup after extraction is not yet implemented; TTL cleanup remains a follow-up once provider extraction is real.
- `ToolExecutionPolicy` is represented by safe provider errors in this slice; full timeout/retry/circuit-breaker policy belongs with provider integrations.

## Improvement Suggestions

- Add provider attempt duration fields when live providers are integrated.
- Add explicit expired-image handling once image extraction reads object bytes.
- Keep sample providers deterministic so frontend and review flows remain stable without paid keys.

## Verification Commands

- `python3 -m py_compile backend/app/config.py backend/app/db.py backend/app/storage.py backend/app/redis_client.py backend/app/health.py backend/app/async_runtime.py backend/app/schemas.py backend/app/workflow_contracts.py backend/app/sample_providers.py backend/app/ranking.py backend/app/workflow.py backend/app/job_repository.py backend/app/object_storage.py backend/app/gateway.py backend/app/routes.py backend/app/main.py backend/app/worker.py`
- `docker compose exec api python -m pytest tests/test_worker_orchestration.py`
- `docker compose exec api python -m pytest tests/test_backend_gateway.py tests/test_worker_orchestration.py`
- `docker compose exec api python -m pytest tests`
- `python3 -m unittest backend.tests.test_runtime_infrastructure_static`
