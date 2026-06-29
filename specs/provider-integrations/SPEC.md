# Provider Integrations Spec

Status: Draft for implementation review

Sources:
- `specs/product-prd/PRD.md`
- `specs/technical-design/TECHNICAL_DESIGN.md`

## Objective

Implement provider boundaries for Gemini extraction/explanation, SerpAPI hosted MCP research, tool execution policy, source normalization, and provider modes.

## Context

Provider integrations are where hallucination, prompt injection, unavailable dependencies, quota limits, and source accuracy risks concentrate. All provider calls must be wrapped by validation, policy, and normalization layers.

## Business Rules

- Gemini is the single V1 AI provider for image extraction, text extraction, clarification, and bounded ranking explanations.
- SerpAPI hosted MCP with Google Shopping is the primary V1 research provider.
- SerpAPI is source access; ThriftLens owns `ResearchSourceResult` and `SourceProduct`.
- Prompt-injection text in user input or images must be treated as untrusted evidence, not instructions.
- Sample/test modes must not make live provider calls.
- Live provider smoke tests require explicit opt-in.

## Functional Requirements

- Implement a Gemini provider client/service for:
  - image-to-`ProductReference`
  - text-to-`ProductReference`
  - optional clarification request
  - bounded ranking explanations over provided candidates
- Validate Gemini output against schema.
- Attempt one repair pass for malformed structured output.
- Implement SerpAPI MCP client configuration through `MultiServerMCPClient`.
- Prefer bearer-token auth if supported; otherwise construct path-auth URL server-side only.
- Restrict SerpAPI MCP usage to an allowlisted engine/parameter set for V1.
- Default V1 SerpAPI engine: Google Shopping.
- Normalize SerpAPI results into `SourceProduct`.
- Implement `ToolExecutionPolicy`:
  - timeout
  - bounded retry
  - circuit breaker check
  - structured error normalization
  - safe user-facing messages
- Implement provider modes:
  - `REAL_MODE`
  - `SAMPLE_MODE`
  - `TEST_MODE`
- Provide fixture-backed sample extraction/research data for one image-style flow and one text-description flow.

## Non-Functional Requirements

- Provider keys and secret-bearing URLs must never be logged.
- Automated tests should mock provider calls by default.
- Provider errors should be structured for observability and safe UI display.
- SerpAPI call count should be capped per job.
- Tool/client code should be isolated from workflow and UI code.

## Acceptance Criteria

- Gemini image extraction returns a schema-valid `ProductReference` or structured extraction error.
- Gemini text extraction returns a schema-valid `ProductReference`, clarification request, or structured extraction error.
- Prompt-injection attempts in text do not alter workflow transitions or tool selection.
- SerpAPI MCP calls use only allowed engine/params in V1.
- SerpAPI results normalize into `SourceProduct` with source-backed prices only.
- Missing price is represented as unknown, not estimated.
- SerpAPI auth secrets are not logged and are not returned to frontend responses.
- Sample mode uses deterministic fixtures and labels results sample/static.
- Test mode never calls Gemini or SerpAPI.
- Live provider smoke tests run only when explicitly enabled.

## Error Cases

- Gemini missing key in `REAL_MODE`: explicit provider configuration error.
- Gemini timeout/rate limit: retry only when safe; then structured unavailable error.
- SerpAPI missing key in `REAL_MODE`: explicit provider configuration error.
- SerpAPI quota/rate limit: structured source error and circuit-breaker update.
- SerpAPI invalid response: structured invalid-response error and no raw payload to UI.

## Out of Scope

- Additional research engines beyond Google Shopping in V1.
- Retailer-specific adapters for Amazon/eBay/Walmart in V1 unless added after the core flow works.
- Generated reference images in V1.
