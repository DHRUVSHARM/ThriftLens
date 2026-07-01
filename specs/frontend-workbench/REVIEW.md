# Frontend Workbench Review

Status: Approved for next slice

## Spec Compliance

- Pass: The first screen is the product workbench, not a landing page or chat sidebar.
- Pass: Image and text input modes are explicit, and only the active mode is submitted.
- Pass: The UI submits through `POST /api/research-jobs` and polls `GET /api/research-jobs/{jobId}` until terminal states.
- Pass: Job progress shows named stages: queued, extracting reference, researching sources, ranking results, and complete.
- Pass: Product reference details render after a brief is available.
- Pass: Results render trust summary, freshness, source count, uncertainty notes, price context, closest match, cheaper/similar/premium groups, and possible matches.
- Pass: Product cards show title, source/retailer, price or unknown price, confidence, group label, match reason, freshness, availability, and source link action.
- Pass: Sample/static labeling appears in the workbench status area and result/trust area.
- Pass: `research_unavailable` renders a reference/trust message without fake product cards.
- Pass: Failed jobs render safe user-facing error messages and retry when the API marks the job retryable.
- Pass: Copy/share produces a plain-text summary with source links and sample/static labeling.
- Pass: API endpoint details are isolated in `frontend/lib/api.ts`; shared frontend contracts live in `frontend/lib/types.ts`.
- Pass: Cleanup extracted reusable presentation helpers into `frontend/lib/presentation.ts`.
- Pass: Browser-driven Playwright tests cover core workbench flows with mocked API responses and real UI interaction.

## Acceptance Criteria Coverage

- Text job can be submitted and render progress/result: covered by `e2e/workbench.spec.ts`.
- Image job can be submitted and render progress/result: covered by `e2e/workbench.spec.ts`.
- Sample/static labeling visible: covered by `e2e/workbench.spec.ts`.
- Partial results render correctly: covered by `e2e/workbench.spec.ts`.
- Research unavailable does not render fake cards: covered by `e2e/workbench.spec.ts`.
- No verified match appears separately from possible matches: covered by `e2e/workbench.spec.ts`.
- Source links and match reasons render: covered by `e2e/workbench.spec.ts`.
- Retry/refinement when API allows it: retry implemented from `job.retryable`; lightweight refinement is rerun through editable inputs.
- Copy/share works for completed or partial briefs: covered by `e2e/workbench.spec.ts`.
- No raw provider errors, keys, or secret-bearing URLs exposed: UI only renders `safeError.message` and normalized brief fields.
- Desktop/mobile layout: covered by `e2e/workbench.spec.ts` mobile overflow check and responsive implementation review.
- Input mode explicit and single primary mode: covered by `e2e/workbench.spec.ts`.
- Progress named stages: covered by `JobStatusPanel` implementation and text submission flow.

## Identified Gaps

- No blocking frontend workbench gaps for the implemented V1 slice.
- shadcn/ui dependencies were not added; V1 uses accessible native controls styled with Tailwind to avoid expanding the dependency surface late in the slice.

## Improvement Suggestions

- Add a small frontend test around `buildSummary`, `groupRankedProducts`, and `priceContext` if a JavaScript test runner is introduced.
- Consider extracting UI primitives into local components if more screens are added.

## Verification Commands

- `docker compose build frontend`
- `docker compose build frontend-e2e`
- `docker compose run --rm frontend npm run build`
- `docker compose run --rm frontend-e2e`
- `docker compose up -d --force-recreate frontend`
- `curl http://localhost:3000`
- `docker compose exec api python -m pytest tests/test_backend_gateway.py tests/test_worker_orchestration.py`
- `docker compose exec api python -m pytest tests`
