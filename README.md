# Luma Take-Home

## 1. Original README Provided

Modern engineering is about directing leverage — tools, judgment, taste — toward real outcomes. This take-home is designed around that.

Pick a problem. Build something that works. You have ~1 working day.

**You must use AI coding tools** — Claude Code, Cursor, Codex, whatever you prefer. These problems are scoped so that AI is necessary to ship something real in a day. We want to see how you direct the tools: how you plan, how you course-correct, what you accept, and what you push back on.

---

### Choose a Problem

Pick the one that excites you most. Each option has a **hardest part** — a technical wall, a product judgment call, a messy real-world detail. That's the part we're paying attention to. If you find yourself avoiding it, you've picked the wrong project.

#### 1. Reverse-Engineer an Undocumented API

Pick a website that doesn't have a public API. Reverse-engineer how it really works — auth, request shape, rate limits, pagination, anti-bot — then build a real product on top.

Two hard parts: cracking the system, *and* picking the right product to build with what you've unlocked. A scraped CSV isn't a product. The data you can pull is the constraint — your taste is what turns it into something someone would actually use.

**Crack the system, then ship something people would actually use.**

#### 2. Build the Mini-App You'd Actually Use

Pick a small problem in your own life. Build it as a deployable web app where AI does real work in the core feature — structured output, vision, an agent loop — not as a chat panel bolted on.

Two hard parts: the product call (what to include, what to cut, what makes the thing good enough that you'd open it twice) *and* the AI integration that has to hold up in front of a real user (latency, weird inputs, the times the model is wrong, the failure mode that has to feel okay).

**Build the small thing you'd actually open twice.**

**ThriftLens selection:** I chose option 2. ThriftLens is a product research mini-app where AI does the core perception, extraction, safety gating, search planning, and ranking work.

#### 3. Rebuild the Hard Part — with AI

Pick a feature from an app you admire that you assume took the team months to get right: real-time sync, search ranking, undo history, gesture handling, a vision pipeline, recommendations. Rebuild it. Then use AI to change the equation — replace heuristics with model calls, generate the data, do at runtime what they had to do offline — so you ship in a day what they shipped in a quarter.

Two hard parts: the technical lever (AI changing *how it works*, not just being the tool that wrote it) *and* the product call (knowing what "better" actually means for the feature you picked, and whether your version delivers).

**Rebuild the part that took them months. Let AI do something they couldn't.**

---

### Tips

The candidates who do best don't start by building — they start by getting sharp on the problem. It's easy to either throw everything at the wall or get heads-down on making something work, and miss the more important question: *what's actually worth solving here, and for whom?*

Slow down before you write a line of code. The thinking you do upfront will shape everything.

---

### What We're Looking For

We want real, working software — not a prototype, not a toy. You'll likely focus on a slice of the problem, but that slice should actually work and be something you'd put in front of a user. Show polish where it matters to you — in the UX, the details, the interactions that feel right. Ship a finished product, not a proof of concept.

We expect the result to be better than what an AI would produce on its own with minimal guidance. The AI writes the code; you own the decisions — what to build, how it should work, what to cut, and what to polish. Specifically, we're paying attention to:

- **How you approach new problems** — how you break down ambiguity, decide what to tackle first, and make good decisions with incomplete information
- **How you use AI tools** — not just that you used them, but how you directed them, where you pushed back, and where your judgment shaped the result
- **The unique perspective you bring** — the product instincts, technical taste, or domain insight that made your solution distinct from what anyone else would have built

---

### What to Deliver

#### 1. Working software

Build your solution directly in this repo. It should run. Include setup instructions that work in a fresh Linux container — we will run your code in one during review. If you use Docker, provide a `docker-compose.yml` for one-command setup.

**If your project is deployable, deploy it.** We want to experience what you built, not just read about it. A live URL — whether it's a web app, an API endpoint, or a hosted service — goes a long way. Vercel, Railway, Fly, a VPS, whatever works. Include the URL in your APPROACH.md.

A `.env.example` is included with stub keys for providers we have accounts with (Anthropic, OpenAI, ElevenLabs, Google Cloud, AWS). Copy it to `.env`, use whichever keys your solution needs, and document any others.

**ThriftLens status:** Complete locally. The app runs with `docker compose up --build`; setup and verification commands are in the ThriftLens README section below. Live deployment URL is tracked in `APPROACH.md` and should be filled once deployed. `.env.example` documents the required Gemini/Google and SerpAPI keys with safe placeholders.

#### 2. APPROACH.md

- What you built and why you picked this problem
- Key decisions and tradeoffs
- What you intentionally left out
- What breaks first under pressure
- What you'd build next

**ThriftLens status:** Complete in `APPROACH.md`. It covers product choice, architecture decisions, AI integration, tradeoffs, omitted scope, pressure points, verification, and next steps.

#### 3. Video walkthrough

Record a short video (~5 minutes) showing what you built. Demo the key flows — whether that's a UI walkthrough, a CLI session, or hitting your API — explain your decisions, and highlight anything you're particularly proud of. This is your chance to show us the experience through your eyes.

**Paste your video link (Loom, Google Drive, YouTube, etc.) into `video.md`.**

**ThriftLens status:** Pending final link. Add the walkthrough URL to `video.md` before submission.

#### 4. AI session history

Your AI session logs (Claude Code, Codex, Cursor) are packaged automatically when you run `./submit.sh`. If you used other AI tools (ChatGPT, etc.), export those conversations and include them in your repo before submitting.

This is a required deliverable. We review your AI interaction to understand how you work — how you plan, iterate, and direct the tools.

**ThriftLens status:** Covered by `./submit.sh`, which packages the AI session history during final submission.

---

### Getting Started

```bash
# 1. Extract the challenge archive you downloaded
tar xzf challenge.tar.gz && cd *eng-take-home*

# 2. Create your own private repo and push to it
git init && git add -A && git commit -m "initial"
gh repo create my-take-home --private --source=. --push

# 3. Copy the env file and fill in any keys you need
cp .env.example .env
```

Now build your solution. Commit and push as you go.

---

### Submitting

When you're ready, run the submit script from your repo root:

```bash
./submit.sh
```

This handles everything: packages your AI session history, commits and pushes your latest changes, grants reviewer access, and registers your submission. You'll see a confirmation when it's done.

---

## 2. ThriftLens Product README

ThriftLens is an AI product research workbench. Give it product evidence from an upload, camera capture, text description, or image plus focus note, and it extracts a structured product reference, searches live source-backed candidates, ranks the matches, and explains uncertainty without pretending it found more evidence than it did.

The app is built for the Luma take-home option 2: a deployable mini-app where AI does meaningful work in the core feature.

### What It Does

- Captures product evidence from image upload, browser camera, text, or image plus text refinement.
- Screens unsafe content, prompt-injection intent, non-product requests, and ambiguous product evidence.
- Extracts a structured product reference with product type, visual attributes, assumptions, and confidence.
- Profiles the product category and shopper priorities before search.
- Searches source-backed product results through SerpAPI MCP.
- Normalizes only product-shaped source results before rendering.
- Ranks candidates with deterministic signals plus optional model-assisted explanations.
- Shows grouped alternatives, price context, caveats, source links, copyable brief text, and partial/failure states.
- Retains uploaded images privately for a bounded TTL, then cleans them up with Celery Beat.

### Stack

- `frontend`: Next.js workbench and landing experience
- `api`: FastAPI job gateway
- `worker`: Celery worker running the LangGraph-style product research flow
- `beat`: Celery Beat scheduler for uploaded-image cleanup
- `extraction-mcp`: FastMCP product extraction service
- `discovery-mcp`: FastMCP product discovery/search planning service
- `ranking-mcp`: FastMCP ranking and explanation service
- `postgres`: durable job/result state
- `redis`: Celery broker/cache
- `minio`: temporary private uploaded-image object storage

### Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: http://localhost:3000
- API health: http://localhost:8000/api/health
- API liveness: http://localhost:8000/api/live
- MinIO console: http://localhost:9001

The checked-in `.env.example` is configured for `REAL_MODE` so reviewers can copy it, add provider keys, and test the live path. For a no-key local demo, set:

```env
PROVIDER_MODE=SAMPLE_MODE
```

### Required Provider Keys For Live Mode

For `REAL_MODE`, fill in:

```env
SERPAPI_API_KEY=
GEMINI_API_KEY=
```

One Gemini-compatible key is enough. The app supports `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or the starter-template `GOOGLE_CLOUD_API_KEY`.

Provider sources:

- Gemini / Google AI Studio: https://aistudio.google.com/app/apikey
- SerpAPI: https://serpapi.com/manage-api-key

Do not commit real secrets in `.env`.

### Useful Commands

```bash
# Validate compose config
docker compose config --quiet

# Run backend tests inside the API container
docker compose exec api python -m pytest tests

# Run frontend build
docker compose run --rm frontend npm run build

# Run Playwright checks
docker compose --profile test run --rm frontend-e2e
```

If the stack is not already running, start it first:

```bash
docker compose up --build
```

### Important Environment Variables

All variables are documented in `.env.example`. The most important ones are:

- `PROVIDER_MODE`: `SAMPLE_MODE`, `TEST_MODE`, or `REAL_MODE`
- `NEXT_PUBLIC_API_BASE_URL`: browser-facing API URL
- `CORS_ALLOWED_ORIGINS`: allowed frontend origins for the API
- `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or `GOOGLE_CLOUD_API_KEY`: Gemini-compatible live model key
- `SERPAPI_API_KEY`: live source research key
- `TEXT_SAFETY_MODEL_ENABLED`: enables structured model-assisted text safety classification
- `PRODUCT_UNDERSTANDING_AGENT_ENABLED`: enables bounded product-understanding model flow
- `DISCOVERY_MODEL`: model for product profile and search planning
- `GEMINI_RANKING_ENABLED`: enables optional model-assisted ranking explanations
- `DATABASE_URL`, `REDIS_URL`, and MinIO settings: runtime services
- `MAX_UPLOAD_MB`, `MAX_TEXT_LENGTH`, `MAX_QUEUED_JOBS`, `MAX_ACTIVE_JOBS`: intake bounds
- `IMAGE_RETENTION_SECONDS`, `IMAGE_CLEANUP_BATCH_SIZE`, `IMAGE_CLEANUP_INTERVAL_SECONDS`: private image retention cleanup

### Image Retention

Uploaded and camera-captured images are stored privately in MinIO for a bounded retention window, defaulting to 21,600 seconds, or 6 hours. Celery Beat schedules `cleanup_expired_images`, which removes expired MinIO objects and their `uploaded_images` metadata rows.

Unsafe images follow the same TTL policy as normal images; once blocked, they are not sent to downstream research.

For local cleanup smoke tests, temporarily set:

```env
IMAGE_RETENTION_SECONDS=72
```

### Demo Flow

Good review scenarios:

1. Text-only: `red leather tote bag`
2. Text-only intent guard: `find the top 10 red bags from Amazon`
3. Image-only: upload or capture a clear single product photo.
4. Image plus focus note: upload a crowded product scene and specify the target item.
5. Unsafe or regulated input: confirm the app blocks before source search.
6. Provider/source failure: confirm the app shows a partial or retryable safe state without fake product cards.

### Deployment

The app is Docker Compose-ready and includes a Render Blueprint in `render.yaml` for the same production-shaped service split:

- web frontend
- FastAPI API
- Celery worker
- Celery Beat scheduler
- Extraction MCP service
- Discovery MCP service
- Ranking MCP service
- Postgres
- Redis or managed queue
- S3-compatible object storage

The Render deployment uses:

- `thriftlens-web`: public Next.js web service
- `thriftlens-api`: public FastAPI web service
- `thriftlens-worker`: Celery worker
- `thriftlens-beat`: Celery Beat cleanup scheduler
- `thriftlens-extraction-mcp`, `thriftlens-discovery-mcp`, `thriftlens-ranking-mcp`: private MCP services
- `thriftlens-postgres`: Render Postgres
- `thriftlens-redis`: Render Key Value
- `thriftlens-minio`: private MinIO service with persistent disk

Render setup notes:

1. Create the Blueprint from `render.yaml`.
2. Fill secret dashboard values for `GEMINI_API_KEY` or `GOOGLE_CLOUD_API_KEY` and `SERPAPI_API_KEY`.
3. After Render creates public URLs, set `NEXT_PUBLIC_API_BASE_URL` on `thriftlens-web` to the public API URL. `CORS_ALLOWED_ORIGINS` is committed in `render.yaml` for the deployed web URL plus local development origins.
4. Redeploy `thriftlens-web` after changing `NEXT_PUBLIC_API_BASE_URL`, because the browser-facing API URL is baked into the Next.js build.
5. Keep camera capture behind HTTPS; Render public services provide HTTPS by default.
6. Render probes `/api/live` for lightweight API liveness; use `/api/health` for full Postgres, Redis, MinIO, and provider-key diagnostics.

Local Docker Compose remains the fallback review path. `minio-init` is still used locally, while deployed services also create the MinIO bucket idempotently from the app storage layer.

### Submission

Before submitting:

1. Add the deployed URL to `APPROACH.md` if deployed.
2. Add the walkthrough video link to `video.md`.
3. Run the final smoke checks above.
4. Run:

```bash
./submit.sh
```
