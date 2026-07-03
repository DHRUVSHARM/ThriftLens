# Workbench Redesign Spec

Status: Implemented, awaiting manual local design review

Sources:
- `specs/frontend-workbench/SPEC.md`
- `specs/product-prd/PRD.md`
- `specs/provider-resilience/SPEC.md`

## Objective

Redesign the ThriftLens UI into a sleek, futuristic, interactive product research workbench with a unified input surface, clearer research stages, stronger result hierarchy, and polished failure/refinement states.

## Context

The current UI proves the workflow but still feels like a form plus scroll panels. The next UI pass should make ThriftLens feel like a focused research instrument: calm, fast, source-grounded, visually distinctive, modular, and platform-driven without becoming a marketing page, chat app, or rigid analytics dashboard.

The UI should support the new backend direction:

- Text-only product research.
- Image-only product research.
- Image plus optional target/focus text.
- Ambiguity refinement when the image contains multiple products.
- Safe failure states for unsafe, non-product, rate-limited, and source-unavailable cases.
- Improved provider fallbacks, model routing, and structured input/output states that must be understandable to an end user.

## Product Feel

ThriftLens should feel like a real web app with product pull, not a technical demo.

The interface should make product research feel fast, guided, and satisfying. A user should understand what to do within seconds, feel the platform actively working during research, and receive a brief that feels useful enough to act on.

The UI should create engagement through:

- Immediate usefulness: the first screen makes the core action obvious.
- Visible progress: the research rail makes the system feel active during long provider calls.
- Satisfying output: best match, price context, and alternatives feel like a useful product brief.
- Trust: source-backed labels, links, and uncertainty notes are visible without overwhelming the user.
- Control: refine, retry, copy, and source-opening actions are easy to find.
- Polish: dark mode, crisp typography, tactile controls, stable layout, and responsive behavior.
- Focus: no marketing filler, generic dashboard clutter, chat-like interaction, or wall of panels.

Manual review should use this product-feel test:

If a user uploads a product image or describes a product, the app should feel like it is doing serious product research for them, not merely displaying model output.

## Business Rules

- Use one unified input surface, not visible image/text mode tabs.
- At least one input is required: image, text, or both.
- Optional text should adapt its meaning:
  - without image: describe the product to research
  - with image: describe what to focus on in the image
- The UI must not imply unsupported certainty.
- Sample/static mode must remain visibly labeled.
- Live source-backed product claims must remain tied to source links.
- The first screen must be the product workbench, not a landing page.
- The UI must be platform-driven, not an open-ended Q&A/chat surface.
- The user should not have to decide what to ask next; the platform should present the next useful action.

## Platform-Driven Interaction Model

ThriftLens is a guided product research workbench, not a chat interface.

The product leads the user through structured states:

1. Capture: user provides product evidence as image, text, or both.
2. Interpret: platform extracts and displays the product reference.
3. Research: platform searches source-backed product data.
4. Compare: platform ranks and groups candidates.
5. Explain: platform summarizes evidence, uncertainty, and next actions.
6. Recover: when blocked, platform asks for the minimum useful correction.

User actions should be bounded:

- Start research.
- Add or revise focus text.
- Retry live search.
- Open source.
- Copy research brief.
- Refine product evidence.

Do not use chat bubbles, generic prompt-box language, or open-ended assistant copy such as "How can I help?"

## Explainability and User Understanding

The UI must make the AI workflow understandable without exposing raw internals.

The interface should clearly communicate:

- What the user provided: image, text, or image plus focus text.
- What ThriftLens understood: product type, visible attributes, assumptions, and confidence.
- What the system is doing: current research pipeline stage.
- Why more input is needed: ambiguity, multiple products, non-product image, or insufficient detail.
- What failed and what the user can do: retry, refine, or continue with partial results.
- What is source-backed versus inferred.
- Why a result is ranked or grouped.

Use specific user-facing state copy, for example:

- "Multiple products detected. Add a focus note to continue."
- "Reference extracted, but live source research is unavailable."
- "No verified exact match found. Showing possible alternatives."
- "Provider is rate-limited. You can retry in a few minutes."
- "Using your focus note to identify the target product."

Do not render raw provider errors, raw model output, secret-bearing URLs, or fake fallback products.

## Visual Direction

- Sleek and futuristic, but still utilitarian and review-friendly.
- Modular, interactive, and engaging, without becoming cluttered.
- Integrated workbench feel, not a rigid split-pane form/results layout or generic analytics dashboard.
- High-contrast neutral base with a restrained accent system.
- Avoid one-note purple/blue gradient styling.
- Avoid decorative orbs, bokeh blobs, and marketing hero layouts.
- Use subtle depth, crisp lines, compact typography, and precise spacing.
- Product cards should feel inspectable and source-backed.
- Research stages should feel like an active pipeline, not a spinner.
- Typography, spacing, and color tokens should be designed deliberately instead of relying on browser/system defaults.
- Support light and dark themes, with a visible theme toggle.

## Design System Direction

Use a lightweight in-repo design system rather than installing a broad component library by default.

Rationale:

- The current frontend already uses Tailwind and `lucide-react`.
- The UI needs a custom dashboard identity more than generic prebuilt components.
- A small local component layer is faster to tune during manual browser review.
- Avoid adding large dependency surface unless a component truly needs it.

Implementation direction:

- Build local primitives for `Button`, `IconButton`, `Badge`, `Field`, `Textarea`, `Select`, `Toggle`, `Panel`, `ProductCard`, and `StageRail`.
- Use `lucide-react` icons inside icon buttons and compact actions.
- Use semantic CSS variables for theme tokens.
- Use Radix/shadcn-style interaction patterns where helpful, but do not require full shadcn installation for this pass.
- If accessibility for a primitive becomes risky, add the narrow dependency needed for that primitive rather than adopting a full component set.

## Typography

Refine typography as a first-class design layer.

Requirements:

- Replace the current Arial/Helvetica default with a deliberate app font strategy.
- Prefer a modern grotesk/sans for UI text and a numeric-friendly style for prices, scores, and compact metrics.
- Use a tight but readable type scale:
  - dashboard title/reference: prominent but not hero-sized
  - section headers: compact and scannable
  - product card titles: stable line clamp, no overflow
  - metadata and badges: small but legible
  - prices/confidence metrics: visually distinct
- Use `font-variant-numeric: tabular-nums` for prices, scores, source counts, and stage numbers.
- Letter spacing should stay normal except for small uppercase labels, where restrained tracking is acceptable.
- Do not scale font size with viewport width.
- Ensure all text fits within cards, buttons, chips, and stage rail items across mobile and desktop.

Suggested font approach:

- Use `next/font` so the font is bundled predictably.
- Use a clean UI sans such as Geist or Inter if available in the Next/font ecosystem.
- Keep fallback fonts documented in CSS variables.

## Theme System

Add first-class light/dark theme support.

Requirements:

- Provide a visible theme toggle in the workbench chrome.
- Respect the user's system preference on first visit.
- Persist the user's selected theme in local storage.
- Avoid hydration flicker where practical.
- Both themes must preserve source-backed trust cues, warning/error visibility, and accessible contrast.

Theme tokens:

- `--bg`
- `--bg-elevated`
- `--surface`
- `--surface-raised`
- `--surface-subtle`
- `--border`
- `--border-strong`
- `--text-primary`
- `--text-secondary`
- `--text-muted`
- `--accent`
- `--accent-strong`
- `--success`
- `--warning`
- `--danger`
- `--price`

Palette direction:

- Light theme: crisp neutral base, restrained accent, strong evidence/status colors.
- Dark theme: deep neutral base, luminous but controlled accent, clear separation between panels.
- Avoid a one-note blue/purple gradient theme in either mode.
- Avoid decorative blobs/orbs; use subtle borders, surfaces, and status lighting instead.
- Selected accent direction: neutral graphite/ink base with electric teal highlights for action/status, plus amber warning and red danger states.
- Do not let the accent dominate the whole UI; it should guide attention to active research, primary actions, and important source-backed signals.
- Dark mode should feel like graphite/carbon with controlled teal illumination, not a neon cyber theme.
- Light mode should feel like warm off-white/clean neutral surfaces with graphite text and teal action accents.

## Layout Direction

### Desktop

- Use an integrated modular workbench layout:
  - slim workbench chrome with brand, provider mode, and theme toggle
  - compact command deck/input band
  - horizontal research pipeline/status rail
  - insight header with product reference, source count, price context, confidence, and live/sample label
  - main interactive module area with best match, price context, alternatives, product reference signals, and trust/evidence
- Avoid a clunky two-column split where one side is just "reference" and the other side is just "results."
- Keep the input band accessible without dominating the viewport.
- Make the best match and price context the primary visual anchors.
- Keep trust/evidence details available but visually secondary.
- Use modular sections, but avoid nested card clutter and rigid BI-dashboard styling.
- Recommended desktop module arrangement:
  - first row: best match panel spans the largest area; price context and compact trust/evidence sit beside or near it
  - second row: grouped alternatives span the main width
  - supporting row/side module: reference signals and assumptions are compact chips/details
- Visual balance target:
  - best match plus price context should carry the first glance
  - alternatives should be visible without competing with the best match
  - reference signals and trust/evidence should support confidence, not dominate the page
  - accent glow/outline should be restrained and reserved for active stage, primary action, and high-value source-backed signals
- Command deck behavior:
  - after terminal results, collapse into a refine bar rather than staying fully expanded/sticky
  - when collapsed, it may stay near the top of the workbench but should not consume major vertical space

### Mobile

- Single-column flow.
- Order:
  1. workbench chrome
  2. unified input or collapsed refine bar
  3. research pipeline
  4. insight header
  4. best match
  5. price context
  6. grouped alternatives
  7. reference signals
  8. trust/evidence
  9. actions
- No horizontal scrolling.
- Controls must fit without text clipping.

## Interaction Decisions

- Remove visible `Image`/`Text` segmented mode tabs.
- Unified input contains:
  - optional image dropzone
  - optional text/focus textarea
  - compact budget and preference controls
  - submit button
- Textarea placeholder should respond to image state:
  - no image: `Describe the product you want to find`
  - image present: `What should ThriftLens focus on in this image?`
- Image preview should support remove/replace.
- If image ambiguity blocks research, preserve the uploaded image and prompt for target text.
- The command deck should expand or collapse based on workflow state:
  - empty/initial state: expanded command deck
  - loading/researching state: expanded or compact-but-visible command deck
  - complete/partial/failed state: collapsed refine bar by default
  - needs-refinement state: expanded command deck with focus text emphasized
- Collapsed refine bar must not hide results.
- Collapsed refine bar should summarize current evidence:
  - uploaded image thumbnail when present
  - text/focus note preview when present
  - budget/preference chips
  - refine/new research action
- Full input controls should re-expand when the user chooses to refine or start new research.
- Retry should be available only when API says retryable.
- Copy/share should include live/sample label, price context, source links, and uncertainty notes.

## Research Pipeline UI

Show named stages with status:

- Capture
- Interpret
- Research
- Compare
- Brief

Each stage should support:

- waiting
- active
- complete
- failed
- skipped

Stage UI should show progress without implying exact timing. It should make long provider calls feel understandable.

Stage copy should map backend states to user-friendly language:

- `queued`: preparing research
- `extracting_reference`: interpreting product evidence
- `researching_sources`: searching source-backed products
- `ranking_results`: comparing candidates
- `complete`: research brief ready
- `partial`: reference ready, source research unavailable
- `needs_refinement`: needs focus or clearer evidence
- `failed`: stopped with an actionable reason

## Result Hierarchy

Render results in this order:

1. Research summary:
   - product title/reference
   - confidence
   - price context
   - source count
   - live/sample label
2. Best match:
   - largest product card
   - title, source, price, confidence, reason, source action
3. Alternatives:
   - cheaper
   - similar
   - premium
   - possible matches
4. Product reference:
   - product type
   - color/material/features
   - assumptions
5. Trust/evidence:
   - source coverage
   - freshness
   - uncertainty notes
   - failure/partial details

The visual hierarchy should feel like an interactive workbench:

- Best match receives the strongest visual treatment.
- Price context is visible near the best match.
- Alternatives are compact, grouped, and scannable.
- Product reference details render as structured signals/chips, not a dominant form.
- Trust/evidence appears as compact context that can be scanned or expanded.

### Alternatives Layout

Use stacked grouped modules for alternatives, not tabs.

Rationale:

- Users should see the shape of the market without switching views.
- Cheaper, similar, premium, and possible matches communicate product positioning quickly.
- Mobile naturally stacks grouped sections.
- Possible matches stay visibly separate from confident matches.

Rules:

- Best match stands alone as the primary result.
- Alternatives render below or around the best match as grouped modules:
  - cheaper
  - similar
  - premium
  - possible matches
- Empty groups may collapse or show a compact unavailable state.
- Possible matches use softer styling and clearer uncertainty copy.
- Do not use tabs for V1 unless result volume becomes too large for a readable page.

## Failure and Refinement States

- Rate limited:
  - explain provider is temporarily rate-limited
  - show retry if available
  - do not keep spinner active
- Ambiguous image:
  - explain multiple possible products were detected
  - ask for focus text
  - do not call it a hard error
- Non-product image:
  - explain the image does not look like a product
  - ask for clearer image or text description
- Unsafe image:
  - explain the image cannot be processed
  - ask for a clear product image instead
- Research unavailable:
  - preserve product reference
  - explain source-backed search failed
  - do not render fake product cards
- No verified match:
  - show possible matches separately
  - ask for refinement if needed

Failure states should render as platform guidance modules, not generic error banners.

Each failure/refinement module should include:

- short state title
- one-sentence explanation
- preserved context when available, such as product reference or uploaded image thumbnail
- primary next action
- secondary action when useful

Suggested actions:

- Ambiguous image: focus text input plus `Continue with focus`
- Non-product image: `Replace image` and `Describe product instead`
- Unsafe image: `Replace image`
- Rate limited: `Retry` when retryable
- Research unavailable: `Retry live search` and `Refine evidence`
- No verified match: `Refine evidence`

## Product Reference Editability

Do not build full structured product-reference editing in this pass.

V1 editability should be limited to:

- refining text/focus input
- replacing/removing uploaded image
- adjusting budget/preference controls
- starting a new research run

The extracted reference should be inspectable and understandable, but not editable field-by-field yet.

Rationale:

- Field-by-field editing increases UI complexity and validation surface.
- The current product value is faster source-backed research, not catalog editing.
- Refining evidence is the simpler platform-driven correction path.

## Functional Requirements

- Submit jobs with image, text, or image+text.
- Validate empty input before submission.
- Validate image type and size before submission.
- Render image/focus text refinement for ambiguous inputs.
- Render research pipeline stages from job status.
- Render product reference, best match, grouped alternatives, possible matches, trust details, and copy/share.
- Render a collapsed refine bar after terminal states with a path to re-open full inputs.
- Render light/dark theme toggle and persist selected theme.
- Stop polling terminal states.
- Continue to support sample, partial, failed, complete, and needs-refinement states.

## Non-Functional Requirements

- UI must be responsive and polished across desktop and mobile.
- No raw provider errors, secrets, or secret-bearing URLs may appear.
- No text overlap or horizontal overflow.
- Stable dimensions for upload area, stage rows, product cards, buttons, thumbnails, and controls.
- Accessible labels and keyboard navigation for all inputs/actions.
- Clean frontend code structure must prevent brittle browser behavior and make UI states easy to maintain.
- Automated frontend tests should cover only critical workflow and layout regressions; manual local review is required for design quality.

## Frontend Structure Requirements

Keep page composition, state handling, API calls, and presentation utilities separated.

Recommended structure:

- `frontend/app/page.tsx`: page state orchestration and composition.
- `frontend/components/workbench/UnifiedInput.tsx`: image/text/focus input and submit controls.
- `frontend/components/workbench/ResearchPipeline.tsx`: pipeline stages and status rendering.
- `frontend/components/workbench/InsightHeader.tsx`: product summary, confidence, source count, price context, live/sample label.
- `frontend/components/workbench/BestMatchPanel.tsx`: primary match display.
- `frontend/components/workbench/AlternativesGrid.tsx`: grouped alternatives and possible matches.
- `frontend/components/workbench/ProductCard.tsx`: reusable source-backed product card.
- `frontend/components/workbench/ReferenceSignals.tsx`: extracted product attributes and assumptions.
- `frontend/components/workbench/TrustEvidence.tsx`: source coverage, freshness, uncertainty, ranking explanation.
- `frontend/components/workbench/FailureState.tsx`: rate-limit, unsafe, non-product, ambiguous, and partial states.
- `frontend/lib/api.ts`: API calls only.
- `frontend/lib/types.ts`: app-facing TypeScript contracts.
- `frontend/lib/presentation.ts`: formatting and state mapping helpers.

Components should be small enough that UI states can be reviewed without hunting through one large page file.

## Testing Strategy

Playwright should be a light safety net, not the center of UI design validation.

Critical automated checks:

- Page loads and unified input is usable.
- Text-only mocked complete result renders.
- Image+focus text can be submitted.
- Ambiguous/refinement state renders a clear focus-text recovery path.
- Retryable failure stops polling and shows retry.
- Mobile viewport has no horizontal overflow.

Avoid exhaustive visual-state automation. Design quality should be reviewed manually in the local browser.

## Manual Local Design Review

UI specs require a manual review loop before completion:

1. Spec Architect defines intended layout, interaction states, and visual direction.
2. Software Engineer implements the UI slice with clean component boundaries.
3. Software Engineer runs build/type checks and critical browser smoke tests.
4. Software Engineer starts or confirms the local app is running.
5. User manually reviews the UI locally in browser.
6. User provides visual/product feedback.
7. Software Engineer refines the UI.
8. Repeat until the UI is polished enough.
9. Review Agent signs off only after feedback is addressed or explicitly deferred.

Manual review should cover:

- desktop default viewport
- mobile/narrow viewport
- empty state
- loading/research pipeline
- successful result
- ambiguous image/refinement state
- rate-limited failure
- source-unavailable partial state

## Acceptance Criteria

- User can submit text-only research from the unified input.
- User can submit image-only research from the unified input.
- User can submit image+focus-text research from the unified input.
- Empty input is rejected locally with a clear message.
- Ambiguous image state prompts for focus text instead of guessing.
- Terminal results collapse the command deck into a compact refine bar without hiding results.
- Rate-limited failed job stops polling and shows retryable failure.
- Research-unavailable partial state shows reference without fake cards.
- Best match is visually more prominent than alternatives.
- Alternatives are grouped and scannable.
- Extracted reference is inspectable but not field-editable in this pass.
- Theme toggle switches light/dark mode and persists the choice.
- Trust/evidence details are present without dominating the page.
- Sample/static result labeling remains visible.
- Mobile layout has no horizontal overflow.
- Browser tests cover text, image, image+text, ambiguous/refinement, rate-limited failure, partial research unavailable, and mobile layout.
- UI avoids rigid split-pane/admin-panel feel and uses an integrated modular workbench layout.
- Platform-driven states present the next useful action without open-ended Q&A/chat behavior.
- Manual review confirms the app feels like a desirable product-research web app, not a technical demo.
- Manual local browser review is completed and feedback is addressed or explicitly deferred.

## Implementation Tasks

1. Add local theme tokens, typography defaults, and light/dark theme support.
2. Add a visible theme toggle with persisted user preference.
3. Create lightweight in-repo UI primitives for buttons, badges, panels, fields, and icon actions.
4. Refactor the large page file into workbench components with clear boundaries.
5. Replace visible image/text mode tabs with one unified input command deck.
6. Support text-only, image-only, and image+focus-text submissions.
7. Add collapsed refine bar behavior after terminal states.
8. Add horizontal research rail with user-friendly stage mapping.
9. Add insight header with product reference, confidence, source count, price context, and live/sample label.
10. Add best match panel, price context module, grouped alternatives, reference signals, and trust/evidence modules.
11. Add platform-guidance failure/refinement modules for ambiguous, non-product, unsafe, rate-limited, source-unavailable, and no-verified-match states.
12. Keep Playwright coverage focused on critical flows and mobile overflow.
13. Run frontend build and critical browser smoke tests.
14. Start or confirm the app locally for manual review.
15. Address manual UI feedback or explicitly defer it.
16. Run code-structure-cleanup and Review Agent pass.

## Open Design Questions

- Final visual balance of the desktop module arrangement should be refined through manual local browser review.
- Exact teal shade should be tuned in implementation, but must follow the graphite/electric-teal direction and avoid neon overuse.

## Out of Scope

- User accounts.
- Saved history.
- Chat sidebar.
- Checkout or purchasing.
- Browser extension.
- Full Figma/design-system buildout unless requested separately.
