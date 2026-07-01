# Worker Orchestration Spec

Status: Implemented and reviewed

Sources:
- `specs/product-prd/PRD.md`
- `specs/technical-design/TECHNICAL_DESIGN.md`

## Objective

Implement the Celery worker and LangGraph-style bounded workflow that converts accepted research jobs into validated product references, source-backed product candidates, ranked alternatives, and user-safe research briefs.

## Context

The worker owns long-running work. It should load a durable job, run bounded workflow stages, call provider tools through policy wrappers, update status after each stage, preserve partial results, and write final output to Postgres.

## Business Rules

- Workflow transitions are fixed by server code; model output cannot choose tools or workflow steps.
- The durable artifact after extraction is `ProductReference`.
- Raw image bytes should be deleted after successful extraction when retry is no longer needed, or after TTL expiry.
- Product facts, prices, retailers, availability, URLs, and freshness must come from source results, not model invention.
- Ranking explanations may use Gemini only over provided `ProductReference` and normalized `SourceProduct` candidates.

## Functional Requirements

- Define one Celery task for V1: run a research job by `job_id`.
- Load job input, provider mode, image metadata, and preferences from Postgres.
- Run workflow stages:
  1. `normalizeInput`
  2. `prepareImage`
  3. `extractReference`
  4. `validateReference`
  5. `researchProducts`
  6. `normalizeSources`
  7. `rankProducts`
  8. `buildBrief`
- Update job status:
  - `queued`
  - `extracting_reference`
  - `needs_refinement`
  - `researching_sources`
  - `ranking_results`
  - `complete`
  - `partial`
  - `failed`
  - `expired`
- Preserve partial results when later stages fail.
- Store provider attempts and dependency health updates.
- Use deterministic ranking as the baseline.
- Fall back to deterministic ranking if model-assisted explanation/reranking fails.
- Build `ProductResearchBrief` with trust summary, source counts, freshness notes, uncertainty notes, and user actions.

## Non-Functional Requirements

- Worker should be safe to run concurrently.
- Whole-task Celery retries should be reserved for infrastructure-level failures where rerunning is safe.
- Stage/provider failures inside a running job should usually be handled by `ToolExecutionPolicy`.
- Workflow should be testable with mocked providers.
- No raw provider error should be displayed to users.

## Acceptance Criteria

- A queued sample-mode text job completes and stores a final `ProductResearchBrief`.
- A queued sample-mode image job completes and stores a final `ProductResearchBrief`.
- Invalid model output is repaired once, then fails with a recoverable extraction error if still invalid.
- Research source failure after extraction produces `research_unavailable` or `partial` with preserved `ProductReference`.
- Ranking model failure still returns deterministic ranking when source products exist.
- No verified match produces possible matches/refinement guidance instead of fake exact matches.
- Job state is updated after major stages and can be read by polling.
- Attempt metadata is recorded without secrets.

## Error Cases

- Image expired before extraction: preserve existing `ProductReference` if available, otherwise request re-upload.
- Vision/text extraction fails: job becomes `failed` or `needs_refinement`.
- All research sources unavailable: return product reference plus `research_unavailable`.
- Worker interruption before durable state is saved: Celery may retry the whole task.

## Out of Scope

- Multi-task Celery chords/groups for individual workflow stages.
- Open-ended autonomous agent loops.
- Purchasing, checkout, or external side effects.
