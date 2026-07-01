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
