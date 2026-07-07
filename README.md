# Luma Take-Home


# I have edited the README the contents are divided as follows now :

1) Original README - This is the one provided by luma
2) ThriftLens Product README - This README contains the answers to questions, deliverables links or folder paths, and other documentation location

----------------------------------------------------------------------------------------------------------------------------------------------------------------------
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

#### 2. APPROACH.md

- What you built and why you picked this problem
- Key decisions and tradeoffs
- What you intentionally left out
- What breaks first under pressure
- What you'd build next

#### 3. Video walkthrough

Record a short video (~5 minutes) showing what you built. Demo the key flows — whether that's a UI walkthrough, a CLI session, or hitting your API — explain your decisions, and highlight anything you're particularly proud of. This is your chance to show us the experience through your eyes.

**Paste your video link (Loom, Google Drive, YouTube, etc.) into `video.md`.**

#### 4. AI session history

Your AI session logs (Claude Code, Codex, Cursor) are packaged automatically when you run `./submit.sh`. If you used other AI tools (ChatGPT, etc.), export those conversations and include them in your repo before submitting.

This is a required deliverable. We review your AI interaction to understand how you work — how you plan, iterate, and direct the tools.

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
-


---------------------------------------------------------------------------------------------------------------------------------------------------------------------


## 2. ThriftLens Product README

1) problem selected

I have selected the problem below for the take home :

#### 2. Build the Mini-App You'd Actually Use

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
