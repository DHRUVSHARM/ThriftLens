---
name: code-structure-cleanup
description: Run after each implemented feature works and tests pass. Guides a focused cleanup pass that removes duplicated mechanics, protects service boundaries, and keeps ThriftLens maintainable without changing behavior.
version: 1.1.0
author: David Ondrej / Michael Shimeles interview notes
license: MIT
metadata:
  hermes:
    tags: [agentic-engineering, refactor, service-layer, code-quality]
    related_skills: [agentic-engineering-workflow]
---

# Code Structure Cleanup After Each Feature

## Overview

AI agents often take the easiest path: they create new functions instead of reusing existing ones. A feature can work while still leaving behind duplicated logic, inconsistent validation, repeated API calls, and code that future agents struggle to understand.

Run this cleanup pass after each feature works and relevant tests pass, not before.

## When to Use

- A feature works locally but the code feels duplicated or messy.
- The agent created similar helper functions in multiple files.
- Future agents need a smaller, cleaner feature area before review.
- A feature touches ThriftLens boundaries such as gateway, worker, provider clients, repositories, object storage, ranking, or UI job polling.

Do not use this as permission to redesign the whole app.

## What Service Layer Means

A service layer is a place for reusable mechanics:

- sending an email
- streaming an AI response
- creating a sandbox
- validating a webhook
- calling an external API
- transforming a payload
- parsing or normalizing data
- reading or writing job state
- uploading temporary image objects
- calling Gemini or SerpAPI MCP
- applying timeout/retry/circuit-breaker policy
- mapping internal errors to user-safe responses

The UI, route, or action decides what should happen. The service handles how it happens.

## ThriftLens Boundary Rules

During cleanup, preserve these architecture boundaries:

- FastAPI routes validate requests and call services; they should not run LangGraph workflows or provider logic.
- Celery tasks load job state and invoke workflow services; they should not duplicate gateway validation or UI response mapping.
- Workflow graph nodes coordinate stages; provider-specific API details belong in provider clients.
- `ToolExecutionPolicy` owns timeout, retry, circuit breaker, and provider error normalization.
- Repositories own Postgres persistence; business logic should not be scattered through raw SQL calls.
- Object storage services own MinIO access; raw image bytes should not leak into unrelated modules.
- Normalizers convert provider results into ThriftLens contracts such as `SourceProduct`.
- UI components render state and call API clients; they should not duplicate ranking, provider, or persistence logic.
- Domain policy stays near the workflow/ranking layer; generic services should handle mechanics.
- Secrets and secret-bearing URLs must never be logged while refactoring.

## Cleanup Prompt

```md
The feature is working. Now do a code-structure cleanup pass.

Goal:
- Find duplicated runtime mechanics, repeated API calls, repeated parsing, repeated validation, or repeated business logic.
- Move repeated mechanics into reusable service-layer functions/modules.
- Keep domain policy in the calling route/action/component.
- Preserve gateway, worker, provider, repository, object-storage, ranking, and UI boundaries.
- Do not change user-facing behavior.
- Keep the diff small.

Process:
1. Inspect the files touched by the feature.
2. Identify repeated logic and name the duplication clearly.
3. Identify any boundary violations against the ThriftLens architecture.
4. Propose the smallest service-layer extraction or boundary correction.
5. Implement it.
6. Run the relevant tests/typechecks.
7. Summarize exactly what got simpler and which boundaries were preserved.
```

## Good Outcome

Instead of four files each having their own slightly different `sendEmail()` logic, there is one tested email service that all four files call.

## Common Pitfalls

1. Refactoring the whole app. Keep the scope tied to the feature.
2. Renaming everything. Naming churn makes PRs hard to review.
3. Mixing cleanup with a new feature. Cleanup is a separate pass.
4. Only formatting code. Pretty code can still contain duplicated logic.
5. Moving domain policy into services. Services should handle mechanics, not business decisions.
6. Moving provider-specific response shapes into UI contracts.
7. Letting routes, Celery tasks, or React components duplicate job-state transition logic.
8. Logging provider keys, MCP URLs, object storage credentials, raw images, or raw provider errors.

## Verification Checklist

- [ ] User-facing behavior stayed the same.
- [ ] Repeated mechanics were actually reduced.
- [ ] Calling files became simpler.
- [ ] Gateway, worker, provider, repository, object-storage, ranking, and UI boundaries stayed clear.
- [ ] ThriftLens contracts such as `ProductReference`, `SourceProduct`, and `ProductResearchBrief` remain the app-facing contracts.
- [ ] No raw provider payloads, raw images, secrets, or secret-bearing URLs leaked into logs or UI.
- [ ] Relevant tests/typechecks ran.
- [ ] Diff stayed focused on the feature area.
