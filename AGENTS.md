# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project Context

This repo is for the Luma take-home. The goal is to build real, working software in about one working day while making thoughtful use of AI coding tools. The reviewers are evaluating both the shipped product and the way AI was directed during the build.

Do not treat this as a toy prototype. Pick a narrow slice if needed, but make that slice usable, polished, and runnable by a reviewer in a fresh Linux container.

## What Matters Most

- Ship working software, not a proof of concept.
- Make product decisions intentionally: what to build, what to cut, and where to polish.
- Use AI as part of the core development process, but keep human judgment visible in the result.
- Prefer a small, complete experience over a broad, unfinished one.
- Make the hardest part of the chosen problem explicit and tackle it directly.
- Keep setup, configuration, and review flow simple.

## Problem Direction

The README offers three acceptable directions:

1. Reverse-engineer an undocumented API and build a useful product on top of the data or capability unlocked.
2. Build a deployable mini-app the author would actually use, with AI doing meaningful work in the core feature.
3. Rebuild a hard feature from an admired app, using AI to change how the feature can be built or experienced.

Before implementing, clarify the selected problem, the intended user, the core workflow, and the hardest technical or product risk. Avoid starting with generic scaffolding until the product bet is clear.

## Engineering Expectations

- Build directly in this repository.
- Keep the app runnable from a fresh Linux container.
- Add clear setup and run instructions.
- If Docker is used, provide `docker-compose.yml` for one-command setup.
- Keep environment variables documented in `.env.example`.
- Do not commit real secrets from `.env`.
- Do not modify `.env`, `.take-home-token`, or secret-related files unless explicitly asked.
- Prefer boring, reliable architecture over cleverness.
- Add tests where they reduce review risk, especially around core logic, API integration, parsing, model output handling, or data persistence.
- Handle likely failure modes gracefully, especially AI latency, invalid model output, missing API keys, external service errors, and empty states.

## Product Expectations

- The first user experience should be the actual product, not a marketing page.
- Polish the details that matter to the chosen workflow.
- Make the core interaction easy to demo in a short walkthrough.
- Avoid bolting on AI as a chat sidebar unless chat is truly the product.
- If using AI, make the model's role concrete: structured output, vision, ranking, extraction, agentic workflow, generation, or another central capability.
- Design the fallback path so failures feel understandable rather than broken.

## AI Integration Planning Notes

Prefer use cases where AI is a real product lever, especially when:

- The workflow requires contextual decision-making rather than a fixed rules-only path.
- The domain has many conditional branches or situation-specific logic that benefits from real-time inference.
- The input includes natural, messy data such as free text, screenshots, documents, transcripts, messages, or loosely structured user notes.

If the selected direction uses AI in the core workflow, plan around these risks early:

- Hallucinations: constrain model output with schemas, distinguish extracted facts from assumptions, and let users review or edit AI-generated results before relying on them.
- Interpretability: preserve enough intermediate state to explain why the system made a recommendation, ranking, extraction, or plan.
- Reliability: define explicit success and failure states, validate model output before rendering, and handle missing API keys, invalid output, empty input, provider errors, and timeouts gracefully.
- Latency: design loading states, retries, demo/sample mode, and bounded agent loops so the app remains usable when model calls are slow.
- Security: avoid committing secrets, document required environment variables, minimize sensitive data retention, and avoid side effects without user confirmation.

## Documentation Deliverables

Create or update the following before submission:

- `README.md`: Include setup instructions, run commands, required environment variables, and any deployment URL if applicable.
- `APPROACH.md`: Explain what was built, why this problem was chosen, key decisions and tradeoffs, what was intentionally left out, what breaks first under pressure, and what should be built next.
- `video.md`: Replace the placeholder with the walkthrough video link.
- `.env.example`: Keep all required variables documented with safe placeholder values.

## APPROACH.md Guidance

The approach document should be candid and specific. It should answer:

- What was built?
- Who is it for?
- Why was this problem worth choosing?
- What was the hardest part?
- Where did AI materially change the implementation or user experience?
- Which decisions were made for scope, speed, reliability, or taste?
- What was deliberately omitted?
- What will fail first with more users, larger data, slower models, or worse inputs?
- What would be built next with more time?

## AI Usage Expectations

AI session history is a required deliverable and will be packaged by `./submit.sh`. Agents should work in a way that leaves a useful trail:

- State assumptions before making major choices.
- Prefer incremental implementation and verification.
- Propose a short plan before coding when scope, architecture, or AI behavior is not yet settled.
- Push back on vague or overbroad ideas when a smaller, sharper product would be better.
- Record important product and technical decisions in `APPROACH.md`.
- Keep `APPROACH.md` notes concise; summarize or cut low-value notes without prompting the user for routine documentation edits.
- If using AI providers in the app, document the model/provider choice and failure behavior.

## Submission Checklist

Before running `./submit.sh`, verify:

- The app runs locally from documented commands.
- A fresh setup path exists and does not rely on undeclared global state.
- The core flow works end-to-end.
- Required environment variables are listed in `.env.example`.
- Missing-key and failure states are handled.
- `APPROACH.md` exists and covers the required prompts.
- `video.md` contains the final walkthrough link.
- Tests, linters, or smoke checks have been run where practical.
- Any deployed URL is included in `APPROACH.md`.
- No real secrets are committed.

## Repository Notes

Current starter files include:

- `README.md`: Take-home instructions.
- `submit.sh`: Luma submission script.
- `video.md`: Walkthrough video placeholder.
- `.env.example`: Provider key placeholders.

As the project grows, keep this file updated with stack-specific commands, conventions, and gotchas so future agents can work quickly without rediscovering the basics.

## Agentic Architecture Notes

Refer to these guidelines during the AI integration step of the workflow. Not every use case needs every step, but the selected product should make the model's role, goal, and boundaries explicit.

### Development Principles

- Treat the model as one component in a product workflow, not as the whole product.
- Build around a clear perception, reasoning, action, and memory loop only when the product needs agentic behavior.
- Separate instructions, model calls, tools, parsing, validation, and UI logic.
- Prefer a single-agent or simple routed workflow unless multi-agent complexity clearly improves the product.
- Use planning before action for multi-step tasks.
- Use ReAct-style loops only when the feature needs iterative tool use or external observations.
- Add reflection or self-checking when output quality, correctness, or trust matters.
- Use routing only when different task types require meaningfully different prompts, tools, or logic.

### Agent Loop Steps

- Perceive: The agent observes its environment. This could mean receiving a user message, reading a file, or detecting input from an external source. The input is processed and converted into a form the agent can understand.
- Recall: The agent pulls in relevant context, memories, or background knowledge. This may include past user interactions, persisted app state, retrieved documents, or related information from a vector database.
- Reason and plan: With input and context in hand, the agent decides what to do. This may involve interpreting intent, breaking down the task into steps, identifying missing information, or choosing tools to use.
- Act: The agent executes one or more actions. It might call an API, send a message, update a file, generate a structured artifact, or take another bounded product action.
- Store and learn: After acting, the agent may store new information. This can include updated context, user feedback, or results from an external system. That new data can become part of memory for future tasks.

### Design Priorities

- Latency: avoid unnecessary model calls, use smaller or faster models where possible, and cache deterministic or repeated outputs.
- Reliability: prefer structured outputs, schemas, validation, and clear fallback states over free-form responses.
- Grounding: do not let the model invent facts. Use user-provided input, retrieved context, or explicit uncertainty when information is missing.
- Guardrails: validate inputs and outputs, avoid exposing secrets, and never print `.env` values or tokens.
- Failure recovery: handle model or API failures gracefully with useful error messages, retry only when safe, and allow the user to continue with reduced functionality.
- Modularity: keep AI logic separated from UI and app plumbing so prompts, providers, and validation can be changed independently.
- Human oversight: for uncertain or high-impact outputs, show editable recommendations instead of taking irreversible actions automatically.
- Observability: log important non-sensitive events, model failures, parsing failures, and user-visible errors to make debugging possible.
- Evaluation: define what a good output means for the core flow and test against a few realistic messy inputs.
- Scope: ship one polished end-to-end flow first; cut features that do not improve reliability, usefulness, or demo clarity.

## Spec-Driven Development Workflow

This repository uses Spec-Driven Development (SDD). The top-level project guidelines define what matters for the take-home; this section defines how features move from product intent to implementation.

There are three primary agents:

1. Spec Architect: responsible for specifications.
2. Software Engineer: responsible for implementation.
3. Review Agent: responsible for validating spec compliance and quality.

Each agent has clear responsibilities and must not exceed its role.

### Agent: Spec Architect

Mission:
Create and maintain clear specifications for each system feature.
Specifications are the source of truth for development.

Responsibilities:
- Create files inside the `/specs` directory
- Define business rules
- Define acceptance criteria
- Define functional and non-functional requirements
- Update specifications when behavior changes
- Create or update `tasks.md` when necessary
- Add concise notes to `APPROACH.md` when product or technical decisions become important for the final submission narrative

Expected spec structure:
Each feature must contain:
- Objective
- Context
- Business rules
- Functional requirements
- Non-functional requirements
- Acceptance criteria
- Error cases
- Out of scope

Constraints:
- Do not write code
- Do not modify files in `/src`
- Do not modify files in `/tests`

### Agent: Software Engineer

Mission:
Implement code based on the specifications located in the `/specs` directory.
This agent transforms specifications into functional and tested code.

General rules:
- Always read files in `/specs` before implementing
- Never implement without acceptance criteria
- Code should be simple and readable
- Avoid overengineering

Required workflow:
1. Read specifications from `/specs`
2. Generate `tasks.md` if it does not exist
3. Run the Acceptance Test Generator workflow
4. Implement based on the tasks and test matrix
5. Create or update automated tests
6. Ensure all acceptance criteria pass
7. Update `.env.example`, `README.md`, and related specs for any new or changed environment variables, provider keys, deployment knobs, or paid-service configuration. Use safe placeholders, document which values are secrets, and include where reviewers should get provider keys.
8. Run the `skills/code-structure-cleanup/SKILL.md` workflow after the feature works and tests pass

Testing:
- Prioritize coverage of acceptance criteria
- Tests should be clear and straightforward
- Each acceptance criterion must have at least one corresponding test
- Each implemented code unit must reach at least 90% unit test coverage

Acceptance Test Generator workflow:
- Read the relevant `/specs` feature file before writing tests.
- Extract acceptance criteria, business rules, error cases, and non-functional requirements.
- Create a test matrix that maps each acceptance criterion to at least one automated test.
- Choose test levels deliberately: unit tests for deterministic logic, schema validation, parsing, state transitions, and AI output normalization; integration tests for API routes, persistence, provider wrappers, and server behavior; UI or component tests for critical loading, empty, error, success, and editable-result states.
- Mock AI provider calls by default. Use live model checks only when the spec explicitly requires them.
- Cover AI-specific failure modes when relevant: invalid JSON, malformed structured output, hallucination guardrails, timeout handling, missing API keys, provider errors, fallback or demo mode, and unsupported user input.
- If a test reveals an unclear or missing requirement, pause implementation and update the specification before changing behavior.
- After running tests, summarize acceptance criteria coverage and any remaining manual checks.

Required cleanup skill:
- Run `skills/code-structure-cleanup/SKILL.md` after each feature works and tests pass.
- Keep the cleanup scoped to duplicated mechanics, messy structure, or boundary violations in the feature area.
- Preserve ThriftLens boundaries between gateway, worker, workflow graph, provider clients, tool execution policy, repositories, object storage, ranking, and UI.
- Do not change user-facing behavior or expand product scope during cleanup.
- If cleanup reveals missing or unclear requirements, pause and update the relevant spec before changing behavior.

Constraints:
- Do not invent requirements that are not described
- Do not change behavior without updating the spec
- Do not modify files inside `/specs`
- Do not implement functionality outside the specification

### Agent: Review Agent

Mission:
Ensure that the implementation faithfully follows the specification.
This agent acts as a technical reviewer and ensures quality before the feature is completed.

Responsibilities:
- Compare the code with the specifications in `/specs`
- Validate that all acceptance criteria were implemented
- Verify that tests cover the acceptance criteria
- Identify inconsistencies between spec and implementation
- Suggest clarity or simplification improvements
- Verify that `APPROACH.md` includes any important decisions, tradeoffs, limitations, or follow-up notes introduced by the feature

Required checks:
The Review Agent must verify:
1. Whether the implementation matches the specification
2. Whether all acceptance criteria have corresponding tests
3. Whether there are features implemented outside the spec
4. Whether the code follows good readability practices
5. Whether unnecessary complexity exists
6. Whether `.env.example`, `README.md`, and relevant specs document all environment variables with safe placeholders, paid-key instructions, provider sources, and no real secrets

Review output:
The review must produce a report containing:
- Spec compliance
- Acceptance criteria coverage
- Identified gaps
- Improvement suggestions
If issues are found, the agent must request corrections before the feature can be considered complete.

### Complete Development Flow

1. Spec Architect creates or updates the specification
2. Software Engineer implements the feature
3. Software Engineer creates automated tests
4. Review Agent validates adherence to the spec
5. Corrections are made if necessary
6. The feature is considered complete after Review Agent approval

### Completion Criteria

A feature is considered complete when:
- All acceptance criteria are implemented
- All automated tests pass
- No divergence exists between code and spec
- The Review Agent approves the implementation


## Documentation Policy

When using a framework, SDK, deployment platform, or external API, prefer current official documentation over memory. Before making major implementation decisions, verify setup commands, package names, API usage, environment variable names, and deployment steps against official docs when web search is available.

Use official docs first, then package READMEs or source repos, then community posts only if official docs are insufficient. Summarize the relevant documentation finding before editing code.
