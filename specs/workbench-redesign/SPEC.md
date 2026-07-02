# Workbench Redesign Spec

Status: Draft for review

Sources:
- `specs/frontend-workbench/SPEC.md`
- `specs/product-prd/PRD.md`
- `specs/provider-resilience/SPEC.md`

## Objective

Redesign the ThriftLens UI into a sleek, futuristic product research workbench with a unified input surface, clearer research stages, stronger result hierarchy, and polished failure/refinement states.

## Context

The current UI proves the workflow but still feels like a form plus scroll panels. The next UI pass should make ThriftLens feel like a focused research instrument: calm, fast, source-grounded, and visually distinctive without becoming a marketing page or chat app.

The UI should support the new backend direction:

- Text-only product research.
- Image-only product research.
- Image plus optional target/focus text.
- Ambiguity refinement when the image contains multiple products.
- Safe failure states for unsafe, non-product, rate-limited, and source-unavailable cases.

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

## Visual Direction

- Sleek and futuristic, but still utilitarian and review-friendly.
- Workbench, not dashboard clutter.
- High-contrast neutral base with a restrained accent system.
- Avoid one-note purple/blue gradient styling.
- Avoid decorative orbs, bokeh blobs, and marketing hero layouts.
- Use subtle depth, crisp lines, compact typography, and precise spacing.
- Product cards should feel inspectable and source-backed.
- Research stages should feel like an active pipeline, not a spinner.

## Layout Direction

### Desktop

- Use a three-zone workbench:
  - top command/input band
  - left or center research summary/reference area
  - main results area with best match and grouped alternatives
- Keep the input band accessible without dominating the entire viewport.
- Make the best match visually prominent.
- Keep trust/evidence details available but secondary.

### Mobile

- Single-column flow.
- Order:
  1. unified input
  2. research pipeline
  3. summary/reference
  4. best match
  5. grouped alternatives
  6. trust/evidence
  7. actions
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
- Retry should be available only when API says retryable.
- Copy/share should include live/sample label, price context, source links, and uncertainty notes.

## Research Pipeline UI

Show named stages with status:

- Reading input
- Building product reference
- Searching live sources
- Comparing candidates
- Preparing brief

Each stage should support:

- waiting
- active
- complete
- failed
- skipped

Stage UI should show progress without implying exact timing. It should make long provider calls feel understandable.

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

## Functional Requirements

- Submit jobs with image, text, or image+text.
- Validate empty input before submission.
- Validate image type and size before submission.
- Render image/focus text refinement for ambiguous inputs.
- Render research pipeline stages from job status.
- Render product reference, best match, grouped alternatives, possible matches, trust details, and copy/share.
- Stop polling terminal states.
- Continue to support sample, partial, failed, complete, and needs-refinement states.

## Non-Functional Requirements

- UI must be responsive and polished across desktop and mobile.
- No raw provider errors, secrets, or secret-bearing URLs may appear.
- No text overlap or horizontal overflow.
- Stable dimensions for upload area, stage rows, product cards, buttons, thumbnails, and controls.
- Accessible labels and keyboard navigation for all inputs/actions.
- E2E tests should cover the main visual states with mocked API responses.

## Acceptance Criteria

- User can submit text-only research from the unified input.
- User can submit image-only research from the unified input.
- User can submit image+focus-text research from the unified input.
- Empty input is rejected locally with a clear message.
- Ambiguous image state prompts for focus text instead of guessing.
- Rate-limited failed job stops polling and shows retryable failure.
- Research-unavailable partial state shows reference without fake cards.
- Best match is visually more prominent than alternatives.
- Alternatives are grouped and scannable.
- Trust/evidence details are present without dominating the page.
- Sample/static result labeling remains visible.
- Mobile layout has no horizontal overflow.
- Browser tests cover text, image, image+text, ambiguous/refinement, rate-limited failure, partial research unavailable, and mobile layout.

## Open Design Questions

- Should the input band stay sticky on desktop after results load?
- Should best match and product reference sit side-by-side or stacked in the result summary?
- What accent palette should define the futuristic look without becoming a one-note blue/purple gradient?
- Should alternatives use tabs, segmented sections, or stacked grouped bands?
- How much of the extracted product reference should be editable in this pass?

## Out of Scope

- User accounts.
- Saved history.
- Chat sidebar.
- Checkout or purchasing.
- Browser extension.
- Full Figma/design-system buildout unless requested separately.
