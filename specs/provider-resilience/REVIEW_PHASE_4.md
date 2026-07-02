# Provider Resilience Phase 4 Review

Status: Approved for Phase 4

## Scope Reviewed

- `specs/provider-resilience/SPEC.md`, Phase 4: Model routing
- `backend/app/config.py`
- `backend/app/gemini_provider.py`
- `backend/app/provider_factory.py`
- `backend/app/workflow.py`
- `backend/app/workflow_contracts.py`
- `backend/tests/test_provider_integrations.py`
- `backend/tests/test_worker_orchestration.py`
- `backend/tests/test_runtime_infrastructure_static.py`
- `frontend/lib/types.ts`
- `frontend/app/page.tsx`
- `.env.example`
- `docker-compose.yml`

## Spec Compliance

Pass.

Phase 4 requirements were implemented without adding new research providers, user accounts, or the broader UI redesign spec.

- Gemini task model settings are split by extraction, extraction fallback, repair, and ranking explanation.
- Extraction and image gate operations use one bounded fallback model only for classified rate-limit or provider-unavailable failures.
- Invalid model output, malformed JSON, auth/config errors, unsafe input, and incompatible image fallback models do not trigger model fallback.
- Repair uses `GEMINI_REPAIR_MODEL` and does not route through fallback.
- `GEMINI_RANKING_ENABLED=false` or unset prevents ranking explainer construction in `REAL_MODE`.
- Successful ranking explanations are persisted as `rankingExplanation` and rendered as optional trust context.
- Ranking explanation failures still complete deterministic source-backed ranking.

## Acceptance Criteria Coverage

| Phase 4 criterion | Coverage |
| --- | --- |
| Gemini task-specific model settings are documented and wired | Covered by settings helpers, `.env.example`, Compose env, and runtime static test coverage |
| Extraction fallback is attempted at most once for rate-limit/unavailable failures | Covered by `test_gemini_extraction_fallback_is_bounded_to_configured_failures` and per-operation fallback state |
| Fallback is not used for non-fallback provider errors or identical/unset fallback model | Covered by `test_gemini_extraction_does_not_fallback_for_invalid_model_output` and `test_model_fallback_policy_skips_unset_identical_and_image_incompatible_models` |
| Repair uses `GEMINI_REPAIR_MODEL` without fallback routing | Covered by `test_gemini_repair_uses_repair_model_without_fallback` |
| `GEMINI_RANKING_ENABLED=false` or unset prevents ranking explainer construction in `REAL_MODE` | Covered by `test_real_mode_disables_ranking_explainer_by_default` |
| `GEMINI_RANKING_ENABLED=true` persists ranking explanation as final-brief trust metadata | Covered by `test_real_mode_constructs_ranking_explainer_only_when_enabled` and `test_ranking_explanation_is_persisted_when_enabled_and_successful` |
| Ranking explanation failure does not block deterministic results | Covered by `test_ranking_model_failure_uses_deterministic_fallback` |

## Identified Gaps

No Phase 4 blocking gaps.

The provider-resilience spec is now complete through all four planned phases. The remaining UI polish/redesign work is tracked separately from this spec.

## Quality Notes

- Model routing stays inside `GeminiExtractionProvider` and `GeminiRankingExplainer`.
- Workflow code only decides whether to persist optional ranking explanation metadata.
- Provider factory owns the `REAL_MODE` ranking explainer opt-in.
- App-facing contracts remain in `workflow_contracts.py`; frontend only renders the optional `rankingExplanation` field.
- Cleanup pass kept retry/circuit mechanics in `ToolExecutionPolicy` and tightened malformed JSON handling so invalid output does not masquerade as provider unavailability.

## Verification

- `python3 -m py_compile backend/app/config.py backend/app/gemini_provider.py backend/app/provider_factory.py backend/app/workflow.py backend/app/workflow_contracts.py backend/tests/test_provider_integrations.py backend/tests/test_worker_orchestration.py backend/tests/test_runtime_infrastructure_static.py`
- `python3 -m unittest backend.tests.test_runtime_infrastructure_static`: 5 tests OK
- `docker compose exec api python -m pytest tests/test_provider_integrations.py tests/test_worker_orchestration.py tests/test_runtime_infrastructure_static.py`: 37 passed, 5 skipped
- `docker compose exec api python -m pytest tests`: 59 passed, 5 skipped
- `docker compose config --quiet`
- `docker compose run --rm frontend npm run build`
- `git diff --check`
