ThriftLens Product README - This README contains the answers to questions, deliverables links or folder paths, and other documentation location

**ThriftLens concept summary:** ThriftLens is a source-backed product research app for moments when a user has product evidence but not a clean product name. The user can upload an image, take a camera photo, describe a product in text, or combine image + text to focus the system on one item. ThriftLens then turns that messy evidence into a structured product reference, searches live product sources, ranks candidate matches, and explains the result with source links, caveats, and price context.

AI is central to the product rather than added as a chat sidebar. The app uses a graph-based workflow to perceive the input, decide whether it is safe and product-focused, extract the product reference, plan source searches, call MCP tools, normalize product results, and rank matches. The graph keeps the top-level flow controlled and reviewable, while model-driven steps handle ambiguous product understanding, search planning, and match explanation where fixed rules would be too brittle.

**Why this is worth opening twice:** The product is designed around a recurring, real behavior: people see products in screenshots, marketplace posts, rooms, outfits, shared photos, and store shelves, but often do not know the exact name or where to compare similar options. ThriftLens makes that moment actionable. A user can drop in a shared image, take a quick photo, or add a short focus note like “the lamp on the left” or “the red shirt,” then get source-backed matches and alternatives.

The repeat value comes from exploration and discovery. Each input can reveal products the user would not have known how to search for directly: similar alternatives, cheaper options, premium versions, adjacent styles, and caveats about why something is or is not a strong match. ThriftLens is not just answering one fixed shopping query; it gives users a way to turn visual curiosity into product research they can inspect, refine, compare, and use to discover newer products they might not have considered.


2) Deliverables as mentioned in the README

#### 1. Working software

Build your solution directly in this repo. It should run. Include setup instructions that work in a fresh Linux container — we will run your code in one during review. If you use Docker, provide a `docker-compose.yml` for one-command setup.

**ThriftLens status:** Complete. The app runs from the root `docker-compose.yml` with the production-like service split: frontend, FastAPI API, Celery worker, Celery Beat cleanup scheduler, Postgres, Redis, MinIO, and the three MCP services for extraction, discovery, and ranking.

For a fresh local run:

```bash
cp .env.example .env
```

Then open `.env` and add the two required live-provider keys:

- `GEMINI_API_KEY`: used for image safety, product extraction, product understanding, and ranking explanations.
- `SERPAPI_API_KEY`: used for source-backed product research through SerpAPI MCP.

`.env.example` documents where to get both keys:

- Gemini / Google AI Studio: https://aistudio.google.com/app/apikey
- SerpAPI dashboard: https://serpapi.com/manage-api-key

After adding the keys:

```bash
docker compose down
docker compose up --build
```

Then open:

- Web app: http://localhost:3000
- API health: http://localhost:8000/api/health
- MinIO console: http://localhost:9001

For a no-key smoke demo, set `PROVIDER_MODE=SAMPLE_MODE`, but the intended review path is `REAL_MODE` with `GEMINI_API_KEY` and `SERPAPI_API_KEY`.

**If your project is deployable, deploy it.** We want to experience what you built, not just read about it. A live URL — whether it's a web app, an API endpoint, or a hosted service — goes a long way. Vercel, Railway, Fly, a VPS, whatever works. Include the URL in your APPROACH.md.

**ThriftLens deployment status:** Deployed on Render.

- Live web app: https://thriftlens-web.onrender.com/
- API health check: https://thriftlens-api.onrender.com/api/health

The Render deployment is managed through the root `render.yaml` Blueprint and uses the same production-shaped service split as local Docker Compose: public Next.js frontend, public FastAPI API, Celery worker, Celery Beat cleanup scheduler, private MCP services for extraction/discovery/ranking, Render Postgres, Render Key Value for the queue, and private MinIO object storage.

A `.env.example` is included with stub keys for providers we have accounts with (Anthropic, OpenAI, ElevenLabs, Google Cloud, AWS). Copy it to `.env`, use whichever keys your solution needs, and document any others.

**ThriftLens environment status:** Complete. `.env.example` includes inline notes for every environment variable used by the local Docker Compose setup. For live `REAL_MODE` testing, reviewers only need to provide `GEMINI_API_KEY` and `SERPAPI_API_KEY`; the file also notes where to get both provider keys.

#### 2. APPROACH.md

- What you built and why you picked this problem
- Key decisions and tradeoffs
- What you intentionally left out
- What breaks first under pressure
- What you'd build next

**ThriftLens status:** Complete in `APPROACH.md`. It covers product choice, architecture decisions, AI integration, tradeoffs, omitted scope, pressure points, verification, and next steps. It also includes a development workflow overview that summarizes the `AGENTS.md` guidance, spec/SWE/review loop, skills used, test coverage approach, and manual review process.

#### 3. Video walkthrough

Record a short video (~5 minutes) showing what you built. Demo the key flows — whether that's a UI walkthrough, a CLI session, or hitting your API — explain your decisions, and highlight anything you're particularly proud of. This is your chance to show us the experience through your eyes.

**Paste your video link (Loom, Google Drive, YouTube, etc.) into `video.md`.**

**ThriftLens status:** Added the walkthrough URL to `video.md` before submission.

#### 4. AI session history

Your AI session logs (Claude Code, Codex, Cursor) are packaged automatically when you run `./submit.sh`. If you used other AI tools (ChatGPT, etc.), export those conversations and include them in your repo before submitting.

This is a required deliverable. We review your AI interaction to understand how you work — how you plan, iterate, and direct the tools.

**ThriftLens status:** Covered by `./submit.sh`, which packages the AI session history during final submission. For a reviewer-friendly summary of how the AI workflow was directed, see the development workflow overview in `APPROACH.md`; the raw session history provides the detailed iteration trail.
