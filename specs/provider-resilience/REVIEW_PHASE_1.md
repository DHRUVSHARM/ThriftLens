# Provider Resilience Phase 1 Review

Status: Approved for Phase 1

## Scope Reviewed

- `specs/provider-resilience/SPEC.md`, Phase 1: Provider retry and stuck-job hardening
- `backend/app/tool_policy.py`
- `backend/app/config.py`
- `backend/app/workflow.py`
- `backend/app/gemini_provider.py`
- `backend/app/serpapi_provider.py`
- `backend/tests/test_tool_policy.py`
- `backend/tests/test_worker_orchestration.py`
- `.env.example`
- `docker-compose.yml`

## Spec Compliance

Pass.

Phase 1 requirements were implemented without pulling in the later circuit-breaker, input-gate, or model-routing phases.

- Provider retries now use configurable exponential backoff with jitter.
- Retry-after hints are respected when present.
- `PROVIDER_MAX_RETRIES=0` keeps provider execution to a single attempt.
- Rate limit, quota, timeout, configuration, unavailable, and existing workflow provider errors map to structured safe errors.
- Missing Gemini/SerpAPI provider keys now use the stable `provider_configuration_error` code at the provider boundary.
- Gemini 429 extraction failures persist a failed/retryable job state instead of leaving the job active.
- Worker crash fallback still marks jobs failed/retryable.

## Acceptance Criteria Coverage

| Phase 1 criterion | Coverage |
| --- | --- |
| Gemini `429` during extraction becomes a safe retryable failed job, never a stuck job | Covered by `test_gemini_rate_limit_during_extraction_marks_job_failed_retryable` |
| Provider retries use exponential backoff with jitter | Covered by `test_tool_policy_retries_retryable_provider_error_then_succeeds` and `test_tool_policy_backoff_uses_exponential_delay_with_jitter` |
| `PROVIDER_MAX_RETRIES=0` makes one provider attempt only | Covered by `test_tool_policy_provider_max_retries_zero_makes_single_attempt` |
| Auth/config errors are non-retryable | Covered by `test_tool_policy_non_retryable_provider_error_does_not_retry` and provider configuration normalization |
| Provider retry behavior follows error taxonomy | Covered by policy tests for timeout, unavailable, 429, config, retry-after, and existing workflow errors |
| Worker crash marks failed/retryable instead of leaving active job | Covered by existing `test_worker_fallback_marks_unexpected_crash_failed_retryable` |

## Identified Gaps

No Phase 1 blocking gaps.

The following provider-resilience requirements are intentionally left for later phases:

- Postgres-backed circuit breaker state
- SerpAPI path-auth log redaction hardening
- Image safety/product-suitability gate
- Image plus target text refinement state
- Task-specific model routing and ranking explainer default-off implementation

## Quality Notes

- `ToolExecutionPolicy` remains the owner of timeout, retry, backoff, and provider error normalization.
- Workflow owns user-safe job state transitions and does not inspect raw provider exceptions.
- Provider clients keep provider-specific configuration checks behind their own boundaries.
- No raw provider payloads or secrets were added to logs or user-facing errors.
- Cleanup pass removed unnecessary classifier parameters and kept the diff scoped.

## Verification

- `python3 -m py_compile backend/app/config.py backend/app/tool_policy.py backend/app/workflow.py backend/app/gemini_provider.py backend/app/serpapi_provider.py backend/tests/test_tool_policy.py backend/tests/test_worker_orchestration.py`
- `docker compose exec api python -m pytest tests/test_tool_policy.py tests/test_worker_orchestration.py`: 20 passed
- `docker compose exec api python -m pytest tests`: 40 passed, 5 skipped
- `python3 -m unittest backend.tests.test_runtime_infrastructure_static`: 5 tests OK
- `docker compose config --quiet`
- `git diff --check`
