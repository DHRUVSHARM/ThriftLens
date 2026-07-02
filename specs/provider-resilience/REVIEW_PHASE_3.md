# Provider Resilience Phase 3 Review

Status: Approved for Phase 3

## Scope Reviewed

- `specs/provider-resilience/SPEC.md`, Phase 3: Input gate and image+text targeting
- `backend/app/workflow_contracts.py`
- `backend/app/workflow.py`
- `backend/app/job_repository.py`
- `backend/app/gateway.py`
- `backend/app/routes.py`
- `backend/app/schemas.py`
- `backend/app/gemini_provider.py`
- `backend/app/sample_providers.py`
- `backend/tests/test_worker_orchestration.py`
- `backend/tests/test_backend_gateway.py`
- `backend/tests/test_provider_integrations.py`
- `.env.example`
- `docker-compose.yml`

## Spec Compliance

Pass.

Phase 3 requirements were implemented without adding the model-routing/ranking-explainer changes from Phase 4 or the broader UI redesign spec.

- Image jobs now run a schema-validated `ImageGateResult` before product extraction.
- Unsafe images fail safely before extraction or source research.
- Non-product and ambiguous images enter `needs_refinement` before extraction or source research.
- Optional `targetDescription` is accepted for image jobs and persisted in the request payload.
- Multi-product images with sufficient target context can proceed.
- Backend policy enforces gate defaults for unsafe, non-product, unclear/low-confidence, and multi-product/no-target cases instead of trusting the model decision alone.
- Gemini image extraction and gate prompts frame target text as untrusted focus context, not instructions.

## Acceptance Criteria Coverage

| Phase 3 criterion | Coverage |
| --- | --- |
| Unsafe image does not call SerpAPI and returns a safe user-facing message | Covered by `test_unsafe_image_fails_without_research_call` |
| Non-product image does not call SerpAPI and asks for clearer product input | Covered by `test_non_product_image_needs_refinement_without_research_call` |
| Multi-product image without target text returns `needs_refinement` | Covered by `test_multi_product_image_without_target_needs_refinement` |
| Multi-product image with target text can proceed when confidently identified | Covered by `test_multi_product_image_with_target_text_can_proceed` |
| Image+target text preserves fixed workflow and treats target text as untrusted context | Covered by `test_create_image_job_accepts_target_description` and `test_image_extraction_prompt_treats_target_description_as_untrusted_focus_context` |
| Image prompt-injection text does not alter workflow/tool selection | Covered by `test_image_prompt_injection_risk_does_not_alter_fixed_workflow` |

## Identified Gaps

No Phase 3 blocking gaps.

The following provider-resilience requirements remain intentionally open for later work:

- Task-specific model routing
- Ranking explainer default-off implementation
- UI redesign for displaying `needs_refinement` and target-text prompts more elegantly

## Quality Notes

- Gate schema lives in app-facing workflow contracts.
- Gateway owns request validation and target text normalization.
- Workflow owns deterministic gate policy and job state transitions.
- Provider clients own Gemini prompt construction and image model calls.
- Repository owns `needs_refinement` persistence.
- No source research is attempted for blocked image gate states.
- Cleanup pass tightened deterministic gate policy so thresholds are enforced by backend code, not delegated solely to the model.

## Verification

- `python3 -m py_compile backend/app/config.py backend/app/workflow_contracts.py backend/app/job_repository.py backend/app/schemas.py backend/app/routes.py backend/app/gateway.py backend/app/sample_providers.py backend/app/gemini_provider.py backend/app/workflow.py backend/tests/test_worker_orchestration.py backend/tests/test_backend_gateway.py backend/tests/test_provider_integrations.py`
- `docker compose exec api python -m pytest tests/test_worker_orchestration.py tests/test_backend_gateway.py tests/test_provider_integrations.py`: 39 passed
- `docker compose exec api python -m pytest tests`: 51 passed, 5 skipped
- `python3 -m unittest backend.tests.test_runtime_infrastructure_static`: 5 tests OK
- `docker compose config --quiet`
- `git diff --check`
