# Approach Notes

This is a working document. Keep notes concise while the product is being defined and built; finalize the prose before submission.

## What We Built

- Planned build: ThriftLens, an AI-assisted product research workbench that turns an image or text description into a structured product reference, researches source-backed product matches, and presents price context plus alternatives.

## Why This Problem

- Selected direction: build a deployable AI mini-app for a small problem from the author's own life.
- Selection criteria: prefer a real personal pain point or admired feature where AI is a core lever, especially when the workflow requires contextual decision-making, condition-specific logic, and natural or messy input data.

## Key Decisions and Tradeoffs

- Use spec-driven development: Spec Architect defines `/specs`, Software Engineer implements from approved specs, Review Agent checks compliance.
- Treat AI as a bounded product component, not a generic chat sidebar.
- Favor reliable, inspectable AI behavior: structured outputs, validation, explicit uncertainty, editable results, and clear failure states.
- Optimize for one polished end-to-end flow over breadth.

## What We Intentionally Left Out

- Generated reference images, accounts/saved history, price alerts, browser extension flows, checkout, long-term marketplace ingestion, and full structured editing for every product-reference field.
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
- Architecture direction: use production-shaped orchestration with a graph workflow and MCP-style multi-server tool boundary for vision and research capabilities.
- Runtime architecture decision: use a FastAPI Job Gateway for intake/load control, Celery with Redis for accepted background research jobs, and UI polling for status/progress.
- Persistence decision: use Postgres as the durable source of truth for job state, product references, partial briefs, final briefs, and attempt metadata; Redis remains the Celery broker/cache.
- Resilience decision: keep retries, timeouts, circuit breakers, and provider error normalization in a separate tool execution policy layer around MCP calls.
- Prompt-injection decision: treat text and image content as untrusted product evidence; enforce safety through extraction prompts, schema validation, fixed workflow transitions, and restricted MCP tools.
- Gateway decision: use FastAPI for typed validation, upload handling, job creation, polling endpoints, and thin intake control; Docker Compose will absorb the multi-service setup cost.
- AI provider direction: use Gemini as the single V1 model provider for image extraction, text extraction, and bounded ranking explanations; defer generated reference images to V2.
- Research source decision: use SerpAPI's hosted MCP server with Google Shopping as the primary V1 source; normalize results into ThriftLens contracts and treat path-auth MCP URLs as secrets.
- Image handling decision: use MinIO as the V1 S3-compatible temporary object store; store image metadata in Postgres, delete raw images after extraction or TTL, and keep `ProductReference` as the durable artifact.
- Fallback decision: support real, sample, and test provider modes; sample mode must use deterministic fixtures and visibly label results as sample/static instead of pretending they are live research.
- UI decision: use a Next.js workbench, not a landing page or chat sidebar; desktop uses two columns for input/reference and results, while mobile stacks the same flow.
- Implementation planning decision: split the approved technical design into focused implementation specs and require `code-structure-cleanup` after each working feature so service boundaries stay maintainable.
- First implementation slice: scaffolded Docker Compose runtime with frontend, FastAPI API, Celery worker, Postgres, Redis, and MinIO; default provider mode is sample mode so local setup does not require paid keys.
- Runtime infrastructure review: API and worker now share one dependency health collector; Compose validation, static runtime tests, and container-internal API/worker health checks passed.
- Backend gateway slice: added `/api/research-jobs`, polling, retry, text/image validation, MinIO image upload, Postgres metadata persistence, Celery enqueueing, and sample/static completion labeling without live provider calls.
- Database reliability adjustment: kept SQLAlchemy async connection pooling enabled for production via configurable pool settings; tests use async ASGI clients and worker tasks use a persistent async loop to avoid cross-event-loop asyncpg reuse.
- Working product name: ThriftLens.
- PRD moved to product-approved draft; next step is technical design for architecture, data contracts, AI workflow, research client, and UI implementation plan.
- Created first technical design draft at `specs/technical-design/TECHNICAL_DESIGN.md` for architecture, data contracts, AI workflow, reliability, and build phases.
