# Provider Resilience Phase 2 Review

Status: Approved for Phase 2

## Scope Reviewed

- `specs/provider-resilience/SPEC.md`, Phase 2: Circuit breaker and log redaction
- `backend/app/tool_policy.py`
- `backend/app/job_repository.py`
- `backend/app/redaction.py`
- `backend/app/serpapi_provider.py`
- `backend/app/config.py`
- `backend/tests/test_provider_resilience_phase2.py`
- `backend/tests/test_provider_integrations.py`
- `.env.example`
- `docker-compose.yml`

## Spec Compliance

Pass.

Phase 2 requirements were implemented without adding input gating, model routing, or UI redesign behavior from later phases.

- Circuit breaker state is persisted in Postgres through the existing `dependency_health` table.
- Circuits are scoped by provider operation, for example `gemini_extract` and `serpapi_research`.
- Repeated retryable failures open the circuit using configurable threshold/window/cooldown settings.
- Open circuits fail fast with `provider_circuit_open` before provider calls are invoked.
- Expired open circuits allow a half-open probe and close on success.
- SerpAPI path-auth URLs and provider keys are redacted through a reusable helper before appearing in sanitized summaries.

## Acceptance Criteria Coverage

| Phase 2 criterion | Coverage |
| --- | --- |
| Circuit breaker state is shared through Postgres | Covered by `test_postgres_circuit_opens_after_repeated_provider_failures` |
| Circuit opens after repeated configured failures | Covered by `test_postgres_circuit_opens_after_repeated_provider_failures` |
| Open circuit prevents repeated doomed calls and returns safe state | Covered by `test_open_circuit_fails_fast_without_invoking_provider` |
| Cooldown expiry allows half-open probe and success closes circuit | Covered by `test_expired_open_circuit_allows_probe_and_success_closes_circuit` |
| SerpAPI path-auth URLs and provider keys are redacted | Covered by `test_redaction_removes_provider_keys_and_serpapi_path_auth_url` and SerpAPI summary assertions |

## Identified Gaps

No Phase 2 blocking gaps.

The following provider-resilience requirements remain intentionally open for later phases:

- Image safety/product-suitability gate
- Image plus target text refinement state
- Task-specific model routing
- Ranking explainer default-off implementation

## Quality Notes

- SQL persistence remains inside `job_repository`.
- `ToolExecutionPolicy` owns timeout, retry, circuit breaker, and provider error normalization.
- SerpAPI provider still owns MCP configuration, while redaction is reusable service-layer utility code.
- No raw provider payloads, raw images, secrets, or secret-bearing URLs were added to logs or UI.
- Cleanup pass extracted repeated dependency-health row mapping and preserved architecture boundaries.

## Verification

- `python3 -m py_compile backend/app/job_repository.py backend/app/tool_policy.py backend/app/redaction.py backend/app/serpapi_provider.py backend/tests/test_provider_resilience_phase2.py backend/tests/test_provider_integrations.py`
- `docker compose exec api python -m pytest tests/test_provider_resilience_phase2.py tests/test_tool_policy.py tests/test_provider_integrations.py`: 24 passed
- `docker compose exec api python -m pytest tests`: 44 passed, 5 skipped
- `python3 -m unittest backend.tests.test_runtime_infrastructure_static`: 5 tests OK
- `docker compose config --quiet`
- `git diff --check`
