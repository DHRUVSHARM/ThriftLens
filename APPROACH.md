# APPROACH.md

## What Was Built

ThriftLens is a deployable AI product research workbench. A user can upload a product image, describe a product in text, or combine an image with a short focus note. The app turns that evidence into a structured product reference, searches source-backed product results, ranks possible matches, and presents price context, alternatives, evidence, and uncertainty in a polished web interface.

The core workflow is:

1. Capture product evidence from image and/or text.
2. Screen the input for unsafe content, prompt-injection intent, non-product requests, and ambiguous image evidence.
3. Extract a structured `ProductReference`.
4. Classify what kind of product it is and how people usually shop for it.
5. Plan and execute bounded source-backed product searches through SerpAPI MCP.
6. Normalize only product-shaped source results.
7. Rank candidates with deterministic signals plus optional model-assisted reasoning.
8. Show best available matches, grouped alternatives, caveats, source links, and price context.

## Who It Is For

The target user is someone who sees or imagines a product but does not know exactly what it is, what it should cost, or what similar options exist. The first useful slice is everyday consumer product research: clothing, bags, furniture, home goods, electronics, and similar standard retail products.

## Why This Problem

This matched README option 2: a deployable mini-app where AI does meaningful work in the core feature. The problem is small enough to ship, but messy enough that a fixed form or simple keyword search is not enough. Images, vague descriptions, crowded scenes, product ambiguity, and source noise all benefit from AI perception and reasoning, as long as the system keeps the model bounded and grounded.

The product hook is: "Show ThriftLens a product, or describe the product you mean, and get source-backed matches without guessing."

## Hardest Part

The hardest part was not calling a vision model. The hard part was making the result trustworthy:

- distinguish product evidence from user instructions
- avoid prompt-injection and unsafe category leakage
- avoid guessing when an image is ambiguous
- prevent generic web links from being rendered as products
- keep source-backed facts separate from model assumptions
- make ranking explainable without overclaiming exact matches
- handle live provider failures without fake results or endless polling

This became the main architecture driver.

## Where AI Matters

AI is used as a bounded component inside the product workflow, not as a chat sidebar.

- Gemini screens image safety and product suitability.
- Gemini/text safety classifies text intent in `REAL_MODE` with deterministic policy fallback.
- Gemini extracts structured product references from image/text.
- Product discovery uses model-assisted product profiling: product family, shopper priorities, important details, and search strategy.
- Search planning selects bounded allowed engines and query strategies, while code validates the plan before execution.
- Ranking uses source-backed candidates with deterministic scoring plus optional model-assisted score/explanation overlays.

The app shows user-safe uncertainty instead of hiding it.

## Key Decisions And Tradeoffs

- **Challenge direction:** chose the AI mini-app path instead of reverse engineering or rebuilding an existing feature.
- **Architecture:** moved from a fixed workflow pipeline to a LangGraph state machine with modular MCP servers.
- **MCP boundaries:** split capabilities into Extraction MCP, Discovery MCP, Ranking MCP, plus a shared MCP runtime for tool discovery, allowlisting, timeout/retry policy, circuit breaker wrapping, and redacted logging.
- **Workflow ownership:** LangGraph owns the stage order and terminal states. Models make bounded judgments inside specific tools.
- **ReAct tradeoff:** an image product-understanding ReAct loop was tested, but Gemini 3.x tool transcripts hit provider `thought_signature` issues through the LangChain bound-tool path. The production path now uses graph-controlled MCP sequencing for product gate, disambiguation, and extraction. This preserves model-powered perception while avoiding fragile tool-call transcript state.
- **Safety:** unsafe text/image handling is centralized through product safety policy plus model-assisted classification. Text input must be a product description or an image refinement note; list/rank/browse/buy/source requests are rejected before search.
- **Research:** SerpAPI hosted MCP is the first live source integration. Results are normalized into `SourceProduct` and must have product-shaped evidence before they appear in the UI.
- **Ranking:** deterministic scoring remains as fallback, but ranking now includes product profile priorities, mismatch caveats, score breakdowns, and source-grounded explanations.
- **Persistence:** Postgres is the durable job state source; Redis/Celery handle background execution; MinIO stores temporary uploaded images.
- **Image retention:** uploaded images are private server-side artifacts retained for the same 21,600-second / 6-hour TTL regardless of whether the image is safe, unsafe, completed, failed, or needs refinement. Celery Beat schedules cleanup so expired MinIO objects and metadata are physically removed without mixing retention policy into graph nodes.
- **Camera perception layer:** camera capture is implemented as a frontend-only source of image evidence. A captured frame becomes the same validated image `File` as upload, so storage, TTL cleanup, safety screening, extraction, and ranking all stay on the existing production path.
- **UX:** the product starts with a designed landing/workbench experience rather than a generic dashboard or chat UI. Progress substates make long-running extraction/search/ranking feel observable.
- **Failure behavior:** no fake live results. Missing sources, provider failures, rate limits, unsafe input, unclear input, and non-product requests become explicit user-facing states.

## What Was Intentionally Left Out

- User accounts and saved history.
- Price alerts and long-term price tracking.
- Checkout or affiliate flows.
- Browser extension/share-sheet capture.
- Full marketplace ingestion beyond SerpAPI-backed source discovery.
- Generated reference images as a primary workflow.
- Manual editing for every extracted product field.
- Deep retailer-specific verification pages for every result.
- Full production deployment to AWS; the app is shaped for it but delivered with Docker Compose.

These were cut to keep the take-home focused on one complete, reviewable AI workflow.

## What Breaks First Under Pressure

- **Provider quota/latency:** Gemini and SerpAPI rate limits can slow or fail jobs. The app handles this with safe errors, partial states, retries, and circuit breakers, but throughput still depends on provider limits.
- **Search coverage:** SerpAPI/Google Shopping may not return enough candidates for obscure products or broad descriptions.
- **Ambiguous evidence:** crowded images and vague text can still require user refinement.
- **Ranking confidence:** exact-match detection is conservative; the app may show "best available match" instead of claiming an exact match.
- **Cost:** model-assisted safety, discovery, and ranking improve quality but add cost; routing and fallbacks are important for production.
- **Infrastructure:** Docker Compose is review-friendly, but real multi-user production would need managed Postgres, object storage, queueing, secrets, observability, and autoscaling.

## Final Status

Implemented and manually tested:

- Docker Compose stack: frontend, FastAPI API, Celery worker, Postgres, Redis, MinIO, Extraction MCP, Discovery MCP, Ranking MCP.
- Celery Beat scheduled image cleanup for expired private uploaded-image artifacts.
- `REAL_MODE` provider path with Gemini and SerpAPI configuration.
- Text-only product descriptions.
- Image-only product evidence.
- Image plus focus note for ambiguous/crowded images.
- Text prompt-injection and non-product intent gating.
- Unsafe/regulated product blocking.
- Image safety and product-likeness gating.
- Source-backed product discovery and normalization.
- Grouped result exploration, best available match behavior, caveats, price context, and copyable brief.
- Partial/failure states for provider/source unavailability.
- Graph-controlled product understanding for Gemini 3.x after ReAct tool-call transcript issues.

Recent verification:

- `docker compose config --quiet` passed.
- `docker compose run --rm api python -m pytest tests` passed: 156 passed, 5 skipped.
- `docker compose run --rm frontend npm run build` passed.
- `python3 -m compileall -q backend/app` passed.
- `docker compose exec -T api sh -lc 'PYTHONPATH=/app pytest /app/tests/test_v2_agent_runner.py -q'` passed.
- `python3 -m py_compile backend/app/agent/product_understanding.py backend/app/agent/graph.py backend/app/worker.py` passed.
- Manual end-to-end testing covered valid text, broad text, prompt-injection text, malformed text, unsafe/regulatory text, clear image, multi-object image, image plus focus note, source failure behavior, grouped results, theme readability, and mobile overflow.

## Deployment

Local Docker Compose is the primary review path:

```bash
cp .env.example .env
docker compose up --build
```

Deployment URL: `TBD`

Render deployment support has been added through `render.yaml`. The hosted shape keeps only the frontend and API public, with Celery worker/beat, Extraction MCP, Discovery MCP, Ranking MCP, Render Postgres, Render Key Value, and private MinIO on Render's private network.

The deployment keeps local Compose as the fallback review path. Render-specific config derives private MCP and MinIO endpoints from service host/port variables, accepts Render's `postgresql://` Postgres URL by converting it for async SQLAlchemy, and creates the MinIO bucket idempotently from the app so deployed MinIO does not need the local `minio-init` container.

Render's platform health check uses `/api/live`, a lightweight API liveness endpoint. The deeper `/api/health` endpoint remains available for the frontend startup check and manual diagnostics because it verifies Postgres, Redis, MinIO, and provider-key configuration.

After Render creates the public services, the remaining manual wiring is:

- set `NEXT_PUBLIC_API_BASE_URL` on `thriftlens-web` to the public API URL
- keep `CORS_ALLOWED_ORIGINS` in `render.yaml` for the public frontend URL plus local development origins
- redeploy the web/API services
- add the verified deployed URL here

## What Would Be Built Next

- Saved research history and user accounts.
- Price tracking and alerts.
- More retailer/search adapters behind the Discovery MCP server.
- Stronger source verification for product detail pages.
- Better product comparison collections.
- More advanced result filtering and sorting.
- Optional generated product-reference images for "I can describe it but do not have a photo" workflows.
- Production deployment with managed Postgres, S3-compatible storage, queue service, secrets manager, OpenTelemetry/CloudWatch logs, and autoscaling worker pools.
