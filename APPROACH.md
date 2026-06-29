# Approach Notes

This is a working document. Keep notes concise while the product is being defined and built; finalize the prose before submission.

## What We Built

- TBD after problem selection and core workflow approval.

## Why This Problem

- Selected direction: build a deployable AI mini-app for a small problem from the author's own life.
- Selection criteria: prefer a real personal pain point or admired feature where AI is a core lever, especially when the workflow requires contextual decision-making, condition-specific logic, and natural or messy input data.

## Key Decisions and Tradeoffs

- Use spec-driven development: Spec Architect defines `/specs`, Software Engineer implements from approved specs, Review Agent checks compliance.
- Treat AI as a bounded product component, not a generic chat sidebar.
- Favor reliable, inspectable AI behavior: structured outputs, validation, explicit uncertainty, editable results, and clear failure states.
- Optimize for one polished end-to-end flow over breadth.

## What We Intentionally Left Out

- TBD per approved spec.
- Default bias: cut features that do not improve usefulness, reliability, or demo clarity.

## What Breaks First Under Pressure

- AI latency, provider failures, invalid model output, hallucinations, and missing API keys are expected pressure points.
- Product scope may break if the workflow expands beyond one clear user job.

## What We Would Build Next

- User accounts and saved research history.
- Price tracking, alerts, and change notifications.
- Browser extension or share-sheet workflow.
- Additional marketplace/search/retailer adapters behind the research client layer.
- Richer generated reference images and multi-turn visual refinement.
- Product comparison collections and broader market research.

## Decision Log

- Initial development process: use spec-driven workflow with explicit Spec Architect, Software Engineer, Acceptance Test Generator, and Review Agent phases.
- Problem category selected: README option 2, a focused AI mini-app where AI does real work in the core feature.
- Created a draft PRD at `specs/product-prd/PRD.md` to capture the product/user/problem definition before implementation specs.
- Current product hypothesis: AI product research app that identifies products from images or text, finds current price context, and suggests similar alternatives with source-backed uncertainty.
- Product hook refined: support both "I have an image of this product" and "I can describe a product idea; help me create/search for something similar."
- Guardrail: generated product concepts are search references, not purchasable listings; the app should use them to find similar real products.
- Architecture direction: keep product research behind a pluggable research client/server boundary, potentially MCP-style, so search APIs and retailer adapters can be decided during technical design.
- Image handling decision: temporarily store uploaded images only to support vision extraction/retry, then delete after TTL; downstream agents should use the structured product reference as the durable artifact.
- Working product name: ThriftLens.
- PRD moved to product-approved draft; next step is technical design for architecture, data contracts, AI workflow, research client, and UI implementation plan.
