# Frontend Workbench Spec

Status: Implemented and reviewed

Sources:
- `specs/product-prd/PRD.md`
- `specs/technical-design/TECHNICAL_DESIGN.md`
- Next.js installation docs: https://nextjs.org/docs/app/getting-started/installation
- Tailwind CSS Next.js install docs: https://tailwindcss.com/docs/installation/framework-guides/nextjs
- shadcn/ui Next.js install docs: https://ui.shadcn.com/docs/installation/next
- lucide-react docs: https://lucide.dev/guide/react
- Playwright installation docs: https://playwright.dev/docs/intro
- Playwright Docker docs: https://playwright.dev/docs/docker

## Objective

Build the ThriftLens product workbench UI for image/text input, job submission, progress polling, product reference review, source-backed results, grouped alternatives, and failure/sample states.

## Context

The first screen should be the actual product. The UI should feel like a practical research workbench, not a marketing landing page or chat sidebar. It must make AI uncertainty and source grounding visible.

## Documentation Findings

- Next.js official docs support creating an App Router application with TypeScript, Tailwind CSS, ESLint, and import aliases through `create next-app`.
- Tailwind CSS has an official Next.js setup path and fits the need for responsive, utility-first workbench styling.
- shadcn/ui has a documented Next.js installation path and gives accessible primitives for controls, tabs, dialogs, badges, buttons, and forms without forcing a heavy visual theme.
- `lucide-react` provides React icons and should be used for compact commands and small UI affordances.
- Playwright Test provides browser-driven UI tests with route-level API mocking; the official Docker image includes browsers/system dependencies, while the project must install the matching `@playwright/test` package separately.

## UI Stack Decision

- Use Next.js App Router, React, and TypeScript for the frontend.
- Use Tailwind CSS for styling.
- Use shadcn/ui primitives selectively for accessible controls and layout primitives.
- Use `lucide-react` for icons.
- Keep the frontend as a separate Docker Compose service that talks to the FastAPI gateway.
- Keep API calls behind a small frontend API client module; React components should not embed endpoint details throughout the tree.
- Implementation note: V1 uses accessible native controls styled with Tailwind rather than adding shadcn/ui dependencies during the build. The component shapes remain compatible with a future shadcn extraction if the design system is expanded.
- Add a separate `frontend-e2e` Docker Compose test service using the official Playwright image so browser tests do not require browsers inside the Alpine app image.

## Business Rules

- Users can start without an account.
- Image upload and text description are both first-class entry points.
- Sample/static data must be visibly labeled.
- Generated/search-reference content must not look like a real product listing.
- Weak matches must be separated from verified matches.
- Exact prices, retailer names, availability, and source URLs must come from source-backed results.
- The UI should render the product workbench as the first screen. Do not create a marketing landing page.
- The UI should not use a chat sidebar as the primary interaction.

## Layout Decision

Use a workbench layout.

Desktop:

- Two-column layout.
- Left column: input, preferences, job status, product reference, and refinement controls.
- Right column: research results, price context, best match, grouped alternatives, possible matches, and source/trust details.
- Keep the left column stable while results update so the user can compare the reference against source-backed results.

Mobile:

- Single-column stacked flow.
- Order: input, progress, product reference, price context, best match, grouped alternatives, possible matches, actions.
- Avoid horizontal scrolling for result cards or controls.

Visual direction:

- Quiet, utility-focused product research surface.
- Compact information density with clear hierarchy.
- Cards are allowed for individual product results, but not nested cards or decorative page-section cards.
- Use a neutral layout with restrained accent color for active states, confidence, and recommendation labels.

## Interaction Decisions

- Use a segmented control or tabs for input mode: `Image` and `Text`.
- V1 submits one active input mode per job. If both image and text are present in the UI, the active mode determines the submitted primary input; the other input is not submitted in V1.
- Use a dropzone/file picker for image upload with file type and size feedback.
- Use a textarea for text description with visible length guidance.
- Use compact controls for:
  - ranking preference
  - optional min/max budget
  - optional currency
  - location/source preference is hidden in V1 and can be added after backend support exists
- Show progress as named stages, not a vague spinner.
- Poll job status until terminal state and let users keep editing a new query while a job is running only if it does not mutate the active job.
- Product reference refinement in V1 should be lightweight:
  - show extracted fields as readable rows/chips
  - allow editing description/preferences and rerunning
  - full structured field editing is out of scope for V1
- Copy/share should create a plain-text summary with source links, confidence, price context, and sample/static label when applicable.

## Result Presentation Decisions

- Top result area should show:
  - job status/completeness
  - sample/static label when applicable
  - price context summary
  - closest verified match when available
- Product cards should show:
  - thumbnail when available
  - title
  - source name
  - price/currency or unknown price
  - confidence label
  - recommendation labels
  - match reason
  - caveats
  - source link action
- Group alternatives into sections:
  - cheaper
  - similar price
  - premium
- Possible matches must appear below verified/grouped alternatives and use lower-confidence visual treatment.
- Partial results must show which source coverage is incomplete without displaying raw provider errors.
- `research_unavailable` must show the product reference and a clear message, not fake product cards.
- No verified match must preserve the reference and offer refinement guidance.

## State Decisions

Terminal states:

- `complete`: render verified matches, alternatives, trust summary, and actions.
- `partial`: render available results with incomplete-source labeling.
- `needs_refinement`: show reference/clarification prompt and rerun controls.
- `failed`: show safe error and retry if allowed.
- `expired`: ask user to rerun or re-upload image.

Provider modes:

- `SAMPLE_MODE`: show a persistent sample/static badge near the status and in the trust summary.
- `REAL_MODE`: never show sample fixtures if provider keys are missing; show explicit configuration/unavailable state.
- `TEST_MODE`: not user-facing.

## Functional Requirements

- Provide a single workbench page with:
  - image upload input
  - text description input
  - ranking preference control
  - optional budget/price range input
  - submit action
- Submit jobs through `POST /api/research-jobs`.
- Poll `GET /api/research-jobs/{job_id}` until terminal state.
- Show progress states:
  - queued
  - extracting reference
  - researching sources
  - ranking results
  - complete/partial/failed/needs refinement
- Render:
  - product reference summary
  - extracted attributes
  - verified matches
  - possible matches
  - price context
  - cheaper/similar-price/premium groups
  - source links
  - confidence labels
  - match reasoning
  - freshness/uncertainty notes
- Support retry/refine/rerun where allowed by job state.
- Support copy/share of the research brief.
- Show clear empty, error, no-match, sample, and partial-result states.
- Render using the workbench layout and state decisions above.

## Non-Functional Requirements

- UI should remain usable while jobs run.
- Polling should stop when a job reaches a terminal status.
- Text and controls must fit on mobile and desktop.
- The UI should be accessible by keyboard and use clear labels.
- Product research results should be scannable and not overloaded with decorative UI.
- No provider secrets or internal error details should appear in the browser.
- UI should avoid decorative hero sections, oversized marketing copy, and purely atmospheric visuals.
- UI should use stable dimensions for upload areas, progress steps, result thumbnails, product cards, controls, and buttons to avoid layout shift.
- UI should use icons for compact commands where familiar icons exist, with accessible labels/tooltips.

## Acceptance Criteria

- User can submit a text-description job and see progress followed by a result.
- User can submit an image job and see progress followed by a result.
- UI clearly labels sample/static results in sample mode.
- UI displays partial results when only some sources respond.
- UI displays `research_unavailable` without fake fallback products.
- UI displays no verified match separately from possible matches.
- UI renders source links and match reasons for product cards.
- UI allows retry/refinement when the API says `canRetry` or `canRefine`.
- UI copy/share action works for completed or partial briefs.
- UI does not expose raw provider errors, keys, or secret-bearing URLs.
- Desktop layout uses a two-column workbench and mobile layout collapses to a single-column flow.
- Input mode is explicit and one primary mode is submitted per job.
- Progress shows named stages.
- Product cards show source, price/unknown price, confidence, match reason, and source action.
- Sample/static labeling is visible in status and trust summary.
- Copy/share output includes source links and sample/static labeling when applicable.

## Error Cases

- Empty input: show validation message before submission.
- Unsupported/oversized image: show validation message.
- Job failed: show safe error and retry if available.
- Job expired: ask the user to rerun or re-upload image.
- Missing provider key in real mode: show configuration/unavailable state.

## Out of Scope

- User accounts.
- Saved history.
- Checkout/purchasing.
- Browser extension.
- Generated reference image editing.
- Full structured field editor for every `ProductReference` field.
