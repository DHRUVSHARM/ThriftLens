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
- [ ] Backend gateway job creation/polling in sample mode.
- [ ] Celery worker sample-mode workflow.
- [ ] MinIO image upload and metadata persistence.
- [ ] Gemini provider integration.
- [ ] SerpAPI hosted MCP integration.
- [ ] Ranking/research brief assembly.
- [ ] Next.js workbench UI.
- [ ] Full acceptance tests and smoke checks.
- [ ] Code-structure-cleanup after each working feature.

## Verification Notes

- Runtime infrastructure Python files passed `python3 -m py_compile`.
- Runtime static tests passed with `python3 -m unittest backend.tests.test_runtime_infrastructure_static`.
- Docker Compose validation passed with `docker compose config --quiet`.
- `docker compose ps` showed frontend, api, worker, postgres, redis, and minio running; Postgres and Redis were healthy.
- API runtime health collector passed inside the API container with Postgres, Redis, MinIO, Gemini config, and SerpAPI config checks true.
- Worker runtime health task passed inside the worker container with Postgres, Redis, MinIO, Gemini config, and SerpAPI config checks true.
- User-facing `curl http://localhost:8000/api/health` was confirmed from the user's terminal before the final health extraction; sandboxed localhost curl was not reachable after restart, so container-internal health verification was used.
- Ran code-structure-cleanup for the runtime slice; extracted repeated health checks into `app.health` and repeated backend service environment config into a Compose YAML anchor.
