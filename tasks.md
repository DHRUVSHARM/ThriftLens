# ThriftLens Implementation Tasks

Status: Active

## Acceptance Test Matrix

### Runtime Infrastructure

| Acceptance criterion | Test level | Planned test |
| --- | --- | --- |
| Docker Compose starts frontend, api, worker, postgres, redis, and minio | Smoke/manual | `docker compose up --build` and health checks |
| API connects to Postgres, Redis, and MinIO | Integration | API `/api/health` reports dependency status |
| Worker connects to Postgres, Redis, MinIO, Gemini config, and SerpAPI config | Integration | Worker health task and dependency check |
| `.env.example` documents required env vars safely | Static | Verify required names exist and no real secrets |
| Postgres stores job, attempt, dependency, and image metadata | Integration | Migration/schema test |
| Redis is not durable product state | Review/unit | No user-visible result repository uses Redis |
| MinIO stores raw images; Postgres stores image metadata only | Integration | Upload metadata path in gateway slice |
| Missing infra/provider config in `REAL_MODE` returns explicit errors | Integration | Health/config checks and gateway validation |

### Backend Gateway

| Acceptance criterion | Test level | Planned test |
| --- | --- | --- |
| Valid text job returns `jobId` and `queued` | Integration | `POST /api/research-jobs` with sample mode |
| Valid image job stores MinIO object and metadata | Integration | Multipart upload with mocked worker enqueue |
| Empty input rejected before queue/provider calls | Unit/integration | Request validation |
| Unsupported/oversized image rejected safely | Unit/integration | Multipart validation |
| Missing provider keys in `REAL_MODE` returns config error | Integration | Provider mode config test |
| `SAMPLE_MODE` succeeds without live keys | Integration | Sample mode job creation |
| Polling returns safe job state | Integration | `GET /api/research-jobs/{id}` |
| Retry endpoint respects retryability | Integration | Retryable/non-retryable jobs |

### Worker Orchestration

| Acceptance criterion | Test level | Planned test |
| --- | --- | --- |
| Sample-mode text job completes | Integration | Celery task with fixture providers |
| Sample-mode image job completes | Integration | Celery task with fixture providers |
| Invalid model output repair/failure path works | Unit | Schema repair tests |
| Research failure preserves `ProductReference` | Unit/integration | Mock source unavailable |
| Ranking model failure uses deterministic fallback | Unit | Ranking tests |
| No verified match gives possible matches/refinement | Unit | Ranking/brief assembly tests |
| Job state updates after major stages | Integration | Repository state assertions |
| Attempts recorded without secrets | Unit/integration | Attempt repository tests |

### Provider Integrations

| Acceptance criterion | Test level | Planned test |
| --- | --- | --- |
| Gemini image/text extraction returns valid schema or error | Unit/integration mock | Provider service tests |
| Prompt injection does not alter workflow/tool selection | Unit/integration | Malicious input fixtures |
| SerpAPI MCP calls use allowed engine/params only | Unit | Client request builder tests |
| SerpAPI results normalize into `SourceProduct` | Unit | Fixture normalization tests |
| Missing price remains unknown | Unit | Normalizer tests |
| Secrets are not logged or returned | Unit/review | Redaction tests |
| Sample/test modes do not call live providers | Unit/integration | Mock assertion tests |
| Live smoke tests require explicit flag | Integration opt-in | `LIVE_PROVIDER_SMOKE=1` only |

### Provider Resilience Phase 1

| Acceptance criterion | Test level | Planned test |
| --- | --- | --- |
| Gemini `429` during extraction becomes a safe retryable failed job, never a stuck job | Unit/integration | Mock extraction provider raises rate-limit-shaped error through `ToolExecutionPolicy`; workflow persists failed/retryable state |
| Provider retries use exponential backoff with jitter | Unit | Inject sleeper/jitter into `ToolExecutionPolicy` and assert bounded delay before retry |
| `PROVIDER_MAX_RETRIES=0` makes one provider attempt only | Unit | Policy call counter remains one after retryable failure |
| Auth/config errors are non-retryable | Unit | Configuration-shaped provider error fails without retry |
| Provider retry behavior follows the error taxonomy | Unit | Policy classifies rate limit, timeout, auth/config, unavailable, and existing `WorkflowProviderError` correctly |
| Worker crash marks failed/retryable instead of leaving a job active | Integration/unit | Existing worker fallback test remains passing |

### Provider Resilience Phase 2

| Acceptance criterion | Test level | Planned test |
| --- | --- | --- |
| Circuit breaker state is shared through Postgres | Integration | Policy failures update `dependency_health` for the provider operation |
| Circuit opens after repeated configured failures | Integration | Repeated provider failures reach threshold and set state/open cooldown fields |
| Open circuit prevents repeated doomed calls and returns safe state | Integration/unit | Policy raises `provider_circuit_open` before invoking provider call |
| Cooldown expiry allows half-open probe and success closes circuit | Integration | Expired open circuit permits one call and resets failure state on success |
| SerpAPI path-auth URLs and provider keys are redacted | Unit | Redaction utility and SerpAPI sanitized summary hide key/path token |

### Provider Resilience Phase 3

| Acceptance criterion | Test level | Planned test |
| --- | --- | --- |
| Unsafe image does not call SerpAPI and returns a safe user-facing message | Unit/integration | Mock image gate returns `fail_safe`; workflow ends failed with `unsafe_image` before research |
| Non-product image does not call SerpAPI and asks for clearer product input | Unit/integration | Mock image gate returns `needs_refinement`; workflow ends `needs_refinement` with `non_product_image` |
| Multi-product image without target text returns `needs_refinement` | Unit/integration | Mock image gate returns multiple products/no target; workflow does not extract or research |
| Multi-product image with target text can proceed when confidently identified | Unit/integration | Image job payload includes `targetDescription`; gate proceeds and workflow completes |
| Image+target text preserves fixed workflow and treats target text as untrusted context | Unit/integration | Gateway accepts `targetDescription`; Gemini prompt frames it as focus context, not instructions |
| Image prompt-injection text does not alter workflow/tool selection | Unit/integration | Gate high injection risk proceeds with warning for clear product or refines when unclear |

### Provider Resilience Phase 4

| Acceptance criterion | Test level | Planned test |
| --- | --- | --- |
| Gemini task-specific model settings are documented and wired | Unit/static | Settings, `.env.example`, and Compose include extraction/fallback/repair/ranking model settings |
| Image gate routes accepted difficult images to quality extraction | Unit/integration | Multi-product with target text and accepted low-confidence images set quality extraction hint; provider uses `GEMINI_EXTRACTION_QUALITY_MODEL` |
| Extraction fallback is attempted at most once for rate-limit/unavailable failures | Unit | Mock Gemini primary model raises 429 and fallback model succeeds once |
| Fallback is not used for non-fallback provider errors or identical/unset fallback model | Unit | Mock non-rate/unavailable failure and assert only primary model is called |
| Repair uses `GEMINI_REPAIR_MODEL` without fallback routing | Unit | Mock repair call captures repair model |
| `GEMINI_RANKING_ENABLED=false` or unset prevents ranking explainer construction in `REAL_MODE` | Unit | Provider factory returns workflow with no ranking explainer |
| `GEMINI_RANKING_ENABLED=true` persists ranking explanation as final-brief trust metadata | Unit/integration | Mock ranking explainer returns summary and final brief includes `rankingExplanation` |
| Ranking explanation failure does not block deterministic results | Unit/integration | Existing failure test remains passing with no `rankingExplanation` |

### Frontend Workbench

| Acceptance criterion | Test level | Planned test |
| --- | --- | --- |
| Text job can be submitted and renders progress/result | UI/component | Mock API flow |
| Image job can be submitted and renders progress/result | UI/component | Mock API flow |
| Sample/static labeling is visible | UI/component | Sample result fixture |
| Partial results render correctly | UI/component | Partial result fixture |
| Research unavailable does not render fake cards | UI/component | Error fixture |
| Possible matches separate from verified matches | UI/component | Result fixture |
| Product cards show source, price/unknown, confidence, reason, action | UI/component | Card fixture |
| Retry/refine actions honor API flags | UI/component | State fixture |
| Copy/share includes links and sample label | Unit/UI | Summary formatter |
| Desktop/mobile layout follows workbench decision | Smoke/manual | Browser viewport checks |

## Implementation Order

- [x] Runtime infrastructure: Compose, API shell, worker shell, Postgres, Redis, MinIO, frontend shell.
- [x] Shared backend schemas, settings, database migrations, and health checks.
- [x] Runtime infrastructure Review Agent pass.
- [x] Backend gateway job creation/polling in sample mode.
- [x] MinIO image upload and metadata persistence.
- [x] Backend gateway Review Agent pass.
- [x] Celery worker sample-mode workflow.
- [x] Deterministic ranking/research brief assembly.
- [x] Worker orchestration Review Agent pass.
- [x] Gemini provider integration.
- [x] SerpAPI hosted MCP integration.
- [x] Provider integrations Review Agent pass.
- [x] Next.js workbench UI.
- [x] Frontend workbench Review Agent pass.
- [x] Full acceptance tests and smoke checks.
- [x] Code-structure-cleanup after each completed feature so far.
- [x] Provider resilience Phase 1: retry/backoff and stuck-job hardening.
- [x] Provider resilience Phase 1 Review Agent pass.
- [x] Provider resilience Phase 2: circuit breaker and log redaction.
- [x] Provider resilience Phase 2 Review Agent pass.
- [x] Provider resilience Phase 3: input gate and image+text targeting.
- [x] Provider resilience Phase 3 Review Agent pass.
- [x] Provider resilience Phase 4: model routing and ranking explainer default-off.
- [x] Provider resilience Phase 4 Review Agent pass.
- [x] Workbench redesign implementation: modular interactive UI, unified input, theme toggle, research rail, and result modules.
- [ ] Workbench redesign manual local design review.
- [ ] Workbench redesign feedback fixes.
- [ ] Workbench redesign Review Agent pass.

## Verification Notes

- Runtime infrastructure Python files passed `python3 -m py_compile`.
- Runtime static tests passed with `python3 -m unittest backend.tests.test_runtime_infrastructure_static`.
- Docker Compose validation passed with `docker compose config --quiet`.
- `docker compose ps` showed frontend, api, worker, postgres, redis, and minio running; Postgres and Redis were healthy.
- API runtime health collector passed inside the API container with Postgres, Redis, MinIO, Gemini config, and SerpAPI config checks true.
- Worker runtime health task passed inside the worker container with Postgres, Redis, MinIO, Gemini config, and SerpAPI config checks true.
- User-facing `curl http://localhost:8000/api/health` was confirmed from the user's terminal before the final health extraction; sandboxed localhost curl was not reachable after restart, so container-internal health verification was used.
- Ran code-structure-cleanup for the runtime slice; extracted repeated health checks into `app.health` and repeated backend service environment config into a Compose YAML anchor.
- Backend gateway Python files passed `python3 -m py_compile`.
- Backend gateway uses production-style SQLAlchemy async pooling with explicit `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` settings.
- Gateway endpoint tests use `httpx.AsyncClient`/`ASGITransport` plus test-only engine disposal between pytest event loops, rather than disabling pooling in app code.
- Celery worker async DB calls use a persistent worker-process event loop via `app.async_runtime` so pooled asyncpg connections are not reused across fresh `asyncio.run` loops.
- Backend gateway tests passed in the API container with `docker compose exec api python -m pytest tests/test_backend_gateway.py`.
- Full API-container backend test command passed with `8 passed, 5 skipped`; skipped tests are repo-root static checks that run from the host with `python3 -m unittest backend.tests.test_runtime_infrastructure_static`.
- Gateway cleanup extracted repeated queue-failure behavior into `enqueue_or_mark_failed`.
- Worker orchestration Python files passed `python3 -m py_compile`.
- Worker orchestration tests passed in the API container with `docker compose exec api python -m pytest tests/test_worker_orchestration.py`.
- Gateway plus worker suites passed together with `docker compose exec api python -m pytest tests/test_backend_gateway.py tests/test_worker_orchestration.py`.
- Full API-container backend test command passed after worker orchestration with `16 passed, 5 skipped`.
- Worker cleanup removed the obsolete repository-level sample completion shortcut so Celery tasks run through `ResearchWorkflow`.
- Provider integration docs were checked against official/current sources: Gemini SDK and structured output docs, SerpAPI hosted MCP docs, and LangChain MCP adapter docs.
- Provider integration Python files passed `python3 -m py_compile`.
- Provider integration tests passed in the rebuilt API container with `docker compose exec api python -m pytest tests/test_provider_integrations.py`; the suite now includes a mocked `MultiServerMCPClient` contract test for LangChain tool invocation.
- Tool execution policy tests passed with `docker compose exec api python -m pytest tests/test_tool_policy.py`, covering healthy success, retryable errors, non-retryable errors, timeouts, degraded health updates, and safe generic error normalization.
- Rebuilt API and worker Docker images after adding provider SDK dependencies, then recreated containers with `docker compose up -d --force-recreate api worker`.
- Full API-container backend test command passed after provider integrations with `30 passed, 5 skipped`.
- Provider cleanup kept provider details behind `GeminiExtractionProvider`, `SerpApiMCPResearchProvider`, `ToolExecutionPolicy`, and workflow factory boundaries; tests now use monkeypatch instead of persistent settings mutation.
- Frontend workbench implemented image/text modes, preferences, job submission, polling, progress stages, product reference summary, grouped result sections, sample labels, retry, and copy/share summary.
- Frontend cleanup extracted API calls into `frontend/lib/api.ts`, shared app-facing contracts into `frontend/lib/types.ts`, and presentation helpers into `frontend/lib/presentation.ts`.
- Added browser-driven Playwright coverage using a separate `frontend-e2e` Docker image/service with mocked API responses for text completion, image validation/submission, partial research-unavailable state, no-verified-match possible results, copy/share, and mobile overflow.
- Frontend image rebuilt with `docker compose build frontend`.
- Frontend e2e image built with `docker compose build frontend-e2e`.
- Production frontend build passed with `docker compose run --rm frontend npm run build`.
- Browser-driven frontend tests passed with `docker compose run --rm frontend-e2e`.
- Frontend service was recreated with `docker compose up -d --force-recreate frontend`; served page was smoke-checked through `curl http://localhost:3000`.
- Gateway/worker contract tests passed after restarting the worker with `docker compose exec api python -m pytest tests/test_backend_gateway.py tests/test_worker_orchestration.py`.
- Full API-container backend test command passed after frontend workbench with `30 passed, 5 skipped`.
- Final acceptance Compose validation passed with `docker compose config --quiet`.
- Final acceptance `docker compose ps` showed frontend, api, worker, postgres, redis, and minio running; Postgres and Redis were healthy.
- Final host smoke check passed for `curl http://localhost:8000/api/health`; API returned `status: ok`, `providerMode: SAMPLE_MODE`, and Postgres/Redis/MinIO/Gemini/SerpAPI configuration checks true.
- Final host smoke check passed for `curl -I http://localhost:3000`; frontend returned HTTP 200.
- Final backend suite passed in the API container with `docker compose exec api python -m pytest tests`: `30 passed, 5 skipped`.
- Final host static runtime tests passed with `python3 -m unittest backend.tests.test_runtime_infrastructure_static`: `5 tests OK`.
- Final frontend production build passed with `docker compose run --rm frontend npm run build`.
- Final browser-driven frontend tests passed with `docker compose run --rm frontend-e2e`: `5 passed`.
- Final whitespace check passed with `git diff --check`.
- Manual browser E2E exposed a missing CORS preflight handler for `POST /api/research-jobs`; fixed with configured FastAPI CORS middleware and regression coverage in `test_browser_preflight_allows_configured_frontend_origin`.
- Post-fix gateway tests passed with `docker compose exec api python -m pytest tests/test_backend_gateway.py`: `9 passed`.
- Post-fix host preflight smoke check returned `HTTP/1.1 200 OK` with `access-control-allow-origin: http://localhost:3000`.
- Live real-mode testing exposed `serpapi_invalid_response` because MCP/LangChain returned wrapped JSON content instead of the direct dict shape used by mock tests.
- SerpAPI provider now unwraps structured-content artifacts, LangChain text blocks, JSON strings, and fenced JSON before normalizing source-backed products.
- Post-fix provider integration tests passed with `docker compose exec api python -m pytest tests/test_provider_integrations.py`: `11 passed`.
- API and worker were recreated after the provider fix; health check returned `providerMode: REAL_MODE`, no missing keys, and all dependency/provider configuration checks true.
- Live real-mode testing exposed jobs stuck at `extracting_reference` after Gemini returned `429 Too Many Requests`; workflow now catches extraction provider failures and persists safe retryable failures instead of letting Celery crash.
- Worker task wrapper now marks unexpected task crashes as retryable failed jobs to avoid indefinite polling states.
- Post-fix worker orchestration tests passed with `docker compose exec api python -m pytest tests/test_worker_orchestration.py`: `10 passed`.
- Post-fix backend gateway tests passed with the live worker stopped to avoid local DB contention: `docker compose exec api python -m pytest tests/test_backend_gateway.py`: `9 passed`; worker was restarted afterward.
- API and worker were recreated after the stuck-job fix; health check returned `providerMode: REAL_MODE`, no missing keys, and all dependency/provider configuration checks true.
- Provider resilience Phase 1 added configurable provider backoff/jitter, retry-after handling, stable provider error classification, and provider-boundary config error normalization.
- Phase 1 regression coverage passed with `docker compose exec api python -m pytest tests/test_tool_policy.py tests/test_worker_orchestration.py`: `20 passed`.
- Full backend suite passed after Phase 1 with `docker compose exec api python -m pytest tests`: `40 passed, 5 skipped`.
- Host static runtime tests passed after Phase 1 with `python3 -m unittest backend.tests.test_runtime_infrastructure_static`: `5 tests OK`.
- Docker Compose validation passed after Phase 1 with `docker compose config --quiet`.
- Code-structure-cleanup for Phase 1 kept retry/error mechanics centralized in `ToolExecutionPolicy`, preserved provider/workflow boundaries, and trimmed unnecessary classifier parameters.
- Provider resilience Phase 1 Review Agent report added at `specs/provider-resilience/REVIEW_PHASE_1.md`; later resilience phases remain open.
- Provider resilience Phase 2 added Postgres-backed circuit breaker state by provider operation, open-circuit fail-fast behavior, half-open recovery, and reusable provider secret/path-auth URL redaction.
- Phase 2 regression coverage passed with `docker compose exec api python -m pytest tests/test_provider_resilience_phase2.py tests/test_tool_policy.py tests/test_provider_integrations.py`: `24 passed`.
- Full backend suite passed after Phase 2 with `docker compose exec api python -m pytest tests`: `44 passed, 5 skipped`.
- Host static runtime tests passed after Phase 2 with `python3 -m unittest backend.tests.test_runtime_infrastructure_static`: `5 tests OK`.
- Docker Compose validation passed after Phase 2 with `docker compose config --quiet`.
- Code-structure-cleanup for Phase 2 kept SQL in `job_repository`, policy mechanics in `ToolExecutionPolicy`, and redaction in a reusable service helper.
- Provider resilience Phase 2 Review Agent report added at `specs/provider-resilience/REVIEW_PHASE_2.md`; input gating and model routing phases remain open.
- Provider resilience Phase 3 added schema-validated image gating, optional image `targetDescription`, `needs_refinement` state persistence, and deterministic backend enforcement for unsafe/non-product/ambiguous gate outcomes.
- Phase 3 regression coverage passed with `docker compose exec api python -m pytest tests/test_worker_orchestration.py tests/test_backend_gateway.py tests/test_provider_integrations.py`: `39 passed`.
- Full backend suite passed after Phase 3 with `docker compose exec api python -m pytest tests`: `51 passed, 5 skipped`.
- Host static runtime tests passed after Phase 3 with `python3 -m unittest backend.tests.test_runtime_infrastructure_static`: `5 tests OK`.
- Docker Compose validation passed after Phase 3 with `docker compose config --quiet`.
- Code-structure-cleanup for Phase 3 kept request validation in the gateway, gate policy in the workflow, Gemini prompts in the provider client, and state persistence in the repository.
- Provider resilience Phase 3 Review Agent report added at `specs/provider-resilience/REVIEW_PHASE_3.md`; model routing remains open.
- Provider resilience Phase 4 added task-specific Gemini model settings, bounded extraction/image-gate fallback routing, gate-driven quality extraction routing, repair-model isolation, and ranking explainer default-off behavior.
- Phase 4 focused regression coverage passed with `docker compose run --rm api python -m pytest tests/test_provider_integrations.py tests/test_worker_orchestration.py tests/test_runtime_infrastructure_static.py`: `41 passed, 5 skipped`.
- Full backend suite passed after Phase 4 with `docker compose run --rm api python -m pytest tests`: `65 passed, 5 skipped`.
- Host static runtime tests passed after Phase 4 with `python3 -m unittest backend.tests.test_runtime_infrastructure_static`: `5 tests OK`.
- Docker Compose validation passed after Phase 4 with `docker compose config --quiet`.
- `.env` and `.env.example` key structure diff check passed after adding quality-routing configuration; `.env` keeps real local values while `.env.example` keeps safe placeholders and reviewer instructions.
- Code-structure-cleanup for Phase 4 preserved provider/workflow/UI boundaries, kept repair on the repair model without fallback cascade, and kept quality routing as a workflow hint consumed by the provider.
- Provider resilience Phase 4 Review Agent report added at `specs/provider-resilience/REVIEW_PHASE_4.md`; provider resilience spec is complete through the planned phases.
- Workbench redesign replaced explicit image/text tabs with a unified input that supports text-only, image-only, and image+focus-text submissions.
- Workbench redesign split the monolithic frontend page into local workbench modules and UI primitives under `frontend/components/workbench`.
- Workbench redesign added light/dark theme tokens, persisted theme toggle, research rail, insight header, best-match-first result hierarchy, price context, grouped alternatives, reference signals, and trust/evidence modules.
- Frontend production build passed after workbench redesign with `docker compose run --rm frontend npm run build`.
- Browser-driven frontend smoke tests passed after workbench redesign with `docker compose run --rm frontend-e2e`: `5 passed`.
- Frontend, API, and worker were rebuilt/recreated for manual review with `docker compose up -d --build frontend` and `docker compose up -d --build worker`.
- Container-internal frontend and API smoke checks passed; host `curl` from this sandbox could not reach localhost despite Compose publishing ports, so manual browser review should use the user's host browser at `http://localhost:3000`.
