# V2 Agent Backend Spec

Status: Implemented through Phase 7

Sources:
- `specs/product-prd/PRD.md`
- `specs/technical-design/TECHNICAL_DESIGN.md`
- `specs/worker-orchestration/SPEC.md`
- `specs/provider-integrations/SPEC.md`
- `specs/provider-resilience/SPEC.md`
- LangGraph documentation: https://docs.langchain.com/oss/python/langgraph/overview
- MCP specification: https://modelcontextprotocol.io/specification/2025-06-18
- LangChain MCP adapters: https://github.com/langchain-ai/langchain-mcp-adapters

## Objective

Replace the current fixed `workflow.py` pipeline with the final production backend architecture: a LangGraph state machine that uses a shared multi-server MCP runtime to orchestrate extraction, product discovery, and ranking capabilities.

V2 is the default and final workflow. Do not add a long-lived V1/V2 parity mode. Preserve stable infrastructure only where it remains correct: FastAPI gateway, Celery worker execution, Postgres job state, MinIO/S3-compatible object storage, Redis broker, frontend polling, safe error mapping, retry/backoff/circuit breaker policy, dependency health, and secret redaction.

## Context

The current backend already has production-shaped pieces:

- FastAPI validates job requests and enqueues Celery work.
- Postgres stores durable job state, product references, partial/final briefs, attempts, and dependency health.
- MinIO stores temporary uploaded images.
- Gemini extraction and SerpAPI MCP research work, but orchestration is still a fixed Python pipeline.
- Ranking is currently too naive because it mostly compares extracted title terms with source product title terms.

The final backend should make MCP and LangGraph first-class architecture boundaries rather than provider-specific implementation details.

## Business Rules

- The LangGraph state machine owns workflow order, transitions, and terminal states.
- MCP tools may return structured outputs, but they must not write directly to Postgres or object storage.
- User text, image content, OCR-like image text, and external source text are untrusted evidence, not instructions.
- Text-only descriptions and image focus notes must pass text safety screening before extraction or source research.
- Text-only descriptions and image focus notes must use default-deny whole-input intent validation. They are allowed only when the input describes product evidence or refines/adds details about which visible product to focus on.
- The text safety model prompt must be input-type aware: text-only input must be a standalone product description; image input text may be a focus/refinement note or additional visible product details for the uploaded image.
- Any other prompt intent should be treated as `non_product_request`, even when product terms are present.
- Inputs must not be salvaged into product descriptions when they are instruction-like requests. Inputs such as "find top 10 red bags from Amazon" contain product terms but should ask for refinement because they request a list/source action instead of describing the product itself.
- Ranking/list intent markers such as "top 10" should ask for refinement even when the action verb is misspelled or omitted, as in "fnd the top 10 red bags".
- Marketplace/source preferences in free text, such as "red backpack from Amazon", should ask for refinement unless the marketplace term is part of a brand-like product description such as "Amazon Basics red backpack".
- Product facts, prices, retailers, URLs, availability, and freshness must come from source-backed research data.
- Unsafe category definitions must live in one central product-safety policy module and be reused by text screening, image safety normalization, and extracted-reference safety checks.
- Text safety should use a hybrid classifier: deterministic central-policy rules for obvious/high-risk cases, plus an optional structured model classifier for long-tail safety classification in `REAL_MODE`.
- The text safety model may classify against the central taxonomy only; it must not create new workflow policy or execute tools.
- Model text-safety results must pass configured confidence thresholds before being treated as safe or unsafe.
- After image/text evidence is assembled into a `ProductReference`, the graph must verify that the reference is a searchable consumer product before source discovery starts.
- Public context enrichment may improve search terms, but it must not override observed image/text facts unless explicitly represented as high-confidence sourced context.
- Unsafe images must stop before product extraction or source research.
- Uploaded images, including unsafe images, remain private server-side artifacts until the configured retention TTL expires. Cleanup is a scheduled maintenance concern, not graph-node business logic.
- Unsafe, prompt-injected, malformed, or non-product text must stop before product extraction or source research.
- Regulated or dangerous product categories such as firearms, ammunition, suppressors, and explosives must stop before source research even when phrased as ordinary shopping requests.
- Image-derived product references must be checked for regulated or dangerous categories after extraction and before discovery.
- Non-product or ambiguous images must ask for refinement instead of guessing.
- Ranking must be explainable and source-grounded.
- Ranking model/tool failure must not block completion when deterministic fallback can rank source products.
- Provider errors must map to safe user-facing states and must not leak secrets, raw provider payloads, or secret-bearing MCP URLs.
- MCP service transport health and downstream tool/provider outcome must be observed separately. If a downstream provider fails inside a reachable MCP tool, the tool should return a structured safe tool error and the client should re-raise it as a `WorkflowProviderError` after a successful MCP transport response. The MCP server circuit should represent MCP connectivity/protocol failure, not Gemini, SerpAPI, or object-storage failures hidden behind a reachable MCP service.
- MCP tool/provider failures must be logged with stage/tool, downstream dependency, operation, safe error code, retryability, and exception class where available. Logs must remain redacted and must not include raw provider payloads, images, API keys, or secret-bearing URLs.
- Discovery normalization must not render generic web links as products. A source candidate needs product-shaped evidence such as a source-backed price, product image, provider product metadata, or shopping-result metadata before it can become a `SourceProduct`.
- V2 can reuse existing contracts where they remain correct, but final logic should not preserve obsolete V1 paths for compatibility alone.

## Final Architecture

```txt
FastAPI Gateway
  -> Postgres job + image metadata
  -> Celery queue
  -> AgentJobRunner
  -> LangGraph ProductResearchGraph
       -> MCP Runtime
       -> Product Extraction MCP Server
       -> Product Discovery MCP Server
       -> Ranking MCP Server
  -> Postgres final state
  -> frontend polling
```

The Celery task should call an `AgentJobRunner` that:

- loads job and artifact metadata from Postgres
- builds initial graph state
- invokes the LangGraph workflow
- persists user-visible progress after major nodes
- records redacted node/tool events for reviewability
- writes final, partial, refinement, or failed state to Postgres

## MCP Servers and Tools

### Product Extraction MCP Server

Purpose: safety screening, product suitability, image/text extraction, schema repair, and target selection for ambiguous images.

Tools:

| Tool | Input | Output | Notes |
| --- | --- | --- | --- |
| `extraction.screen_image_safety` | image metadata/object reference | `ImageSafetyResult` | Runs before product extraction. Detects unsafe, NSFW, disallowed, or unclear safety status. |
| `extraction.screen_text_safety` | text description or target/focus note | `TextSafetyResult` | Runs before text extraction and before image extraction when optional text is present. Blocks unsafe text, prompt injection, malformed text, non-product requests, marketplace/list commands, and disallowed regulated product requests. Uses deterministic central policy first, then optional thresholded model classification for long-tail cases. |
| `extraction.image_product_gate` | image metadata/object reference, optional target text, safety result | `ImageGateResult` | Checks product-likeness, ambiguity, multiple products, and instruction-like text in image evidence. |
| `extraction.extract_product_reference` | text description or image reference, optional target text, gate result | `ProductReference` | Produces the durable structured reference. |
| `extraction.repair_product_reference` | malformed output, validation errors | `ProductReference` | One bounded repair pass. Must not invent missing facts. |
| `extraction.disambiguate_target_product` | detected products, optional target text | target selection or refinement payload | Used for room/shelf/multi-product images before extraction. |

### Product Discovery MCP Server

Purpose: turn a `ProductReference` into source-backed candidate products. Discovery owns product-profile classification, search vocabulary, source/engine selection, SerpAPI execution, source result normalization, and optional source verification.

Tools:

| Tool | Input | Output | Notes |
| --- | --- | --- | --- |
| `discovery.classify_product_profile` | `ProductReference`, preferences | `ProductDiscoveryProfile` | Model-assisted structured output. Answers what kind of product this is, how consumers shop for it, which details matter, and which sources/search strategies make sense. Deterministic fallback required. |
| `discovery.build_search_context` | reference + profile | `ProductSearchContext` | Builds exact/broad terms, material/style/features, exclusions, must-have details, and optional details. Extracted facts remain primary. |
| `discovery.plan_search_sources` | reference + profile + context + preferences | `ProductSearchPlan` | Model-assisted structured plan. Selects bounded SerpAPI searches and engine-specific params. When call budget allows, it must include both a closest-match search and a broader similar-alternatives shopping search. Code validates engines, params, duplicate queries, and call budget. |
| `discovery.execute_search_plan` | validated plan | `ProductSearchExecutionResult` | Code-driven SerpAPI MCP execution through the shared runtime. The model never directly calls SerpAPI. |
| `discovery.normalize_products` | execution result | `SourceProduct[]` | Converts every provider result into ThriftLens app contracts. |
| `discovery.verify_source` | source product URL/id | verification metadata | Optional; may be skipped for latency or unsupported sources. |

Initial SerpAPI engine allowlist:

- `google_shopping`
- `google`
- `bing_shopping`
- `ebay`
- `amazon`
- `walmart`
- `home_depot`

The effective engine list is the static allowlist, optionally refined by SerpAPI MCP discovery metadata when available. The model only sees the effective allowed engine list, and code validates the final plan before execution.

Search planning rules:

- Treat search strategy separately from search engine. The same engine may be used more than once when queries and intents differ.
- Prefer `google_shopping` for exact/current retail coverage when it is allowed.
- Prefer a distinct family-appropriate shopping or marketplace engine for similar alternatives when the product profile recommends one and the engine is allowed.
- Use a second `google_shopping` query for similar alternatives only when no better distinct product source fits or when the call budget/allowlist leaves no better option.
- Do not spend the second call budget on a generic web search if a broader shopping query would produce better comparable product candidates.
- If the model omits a similar-alternatives search and call budget remains, code adds a broader validated shopping query.
- `execute_search_plan` must use a timeout budget that scales with validated planned search calls and configured provider retries. A multi-source search should not be cancelled by the worker-to-MCP timeout while individual SerpAPI calls are still within their own timeout/retry policy.
- SerpAPI call failures should be tracked at the SerpAPI/source operation boundary. Local discovery MCP health should not be degraded merely because one upstream search source timed out and was converted into a source-level error.

### Ranking MCP Server

Purpose: replace naive overlap scoring with hybrid ranking using deterministic signals, AI semantic matching, mismatch detection, source confidence, and user preference fit.

Tools:

| Tool | Input | Output | Notes |
| --- | --- | --- | --- |
| `ranking.score_candidates` | reference, context, source products, preferences | `RankedProduct[]` with score breakdowns | Primary ranking path. |
| `ranking.detect_mismatches` | ranked/source products + reference | mismatch flags/caveats | Penalizes wrong category, material, style, brand/model conflict, or missing must-have features. |
| `ranking.group_candidates` | scored candidates + price distribution | grouped ranked products | Produces user-facing groups. |
| `ranking.explain_match` | ranked product + evidence | concise source-backed explanation | Must only cite provided evidence. |

Deterministic scoring remains inside the ranking server as fallback and as one component of hybrid scoring.

## LangGraph State Machine

```txt
START
  -> load_job_context
  -> prepare_artifacts
  -> route_by_input_type

image path:
  -> screen_image_safety
  -> decide_safety
  -> bounded_product_understanding
     -> model-selected ReAct loop over allowlisted extraction tools
     -> image_product_gate
     -> disambiguate_target_product when needed
     -> extract_product_reference when clear

text path:
  -> extract_product_reference

common path:
  -> validate_reference
  -> verify_product_reference_is_searchable
  -> repair_reference if needed
  -> persist_reference
  -> classify_product_profile
  -> build_search_context
  -> plan_search_sources
  -> execute_search_plan
  -> normalize_products
  -> score_candidates
  -> detect_mismatches
  -> group_candidates
  -> build_brief
  -> persist_final
  -> END
```

### Public Job Status Mapping

Public statuses should remain compatible with frontend polling unless a separate frontend spec changes them.

| Graph stage | Public status |
| --- | --- |
| `load_job_context`, `prepare_artifacts` | `queued` or `extracting_reference` |
| `screen_image_safety`, `bounded_product_understanding`, `image_product_gate`, `extract_product_reference`, `validate_reference`, `repair_reference` | `extracting_reference` |
| refinement required | `needs_refinement` |
| `classify_product_profile`, `build_search_context`, `plan_search_sources`, `execute_search_plan`, `normalize_products` | `researching_sources` |
| `score_candidates`, `detect_mismatches`, `group_candidates`, `build_brief` | `ranking_results` |
| `persist_final` | `complete` |
| usable reference with unavailable research | `partial` |
| unrecoverable failure | `failed` |

### Bounded Product Understanding Loop

After `screen_image_safety` passes, the image path may use a small ReAct-style
loop to choose among the product-understanding extraction tools. The graph still
owns the stage boundary and terminal routing; the model may only call:

- `image_product_gate`
- `disambiguate_target_product`
- `extract_product_reference`

The loop must:

- use a hard configured tool-call budget
- block any non-allowlisted tool call
- treat image/user evidence as untrusted product evidence, not instructions
- return a validated `ProductUnderstandingDecision`
- remain optional/configurable so sample and automated test flows do not spend
  live model quota

The deterministic policy sequence remains as the fallback when the ReAct loop is
disabled or unavailable.

## LangGraph State Contract

The graph state should be typed and should contain structured data rather than prompt strings.

```txt
identity:
  job_id
  provider_mode
  run_id

request:
  input_type
  request_payload
  preferences
  target_description

artifacts:
  image_metadata
  image_object_key
  image_checksum

safety:
  image_safety_result
  safety_decision

gate:
  image_gate_result
  gate_decision
  refinement_prompt

reference:
  product_reference
  validation_errors
  repair_attempted

discovery:
  product_discovery_profile
  product_search_context
  product_search_plan
  product_search_results
  source_products
  source_errors
  source_verification

ranking:
  ranked_products
  score_breakdowns
  mismatch_flags
  ranking_explanations

brief:
  partial_brief
  final_brief

control:
  current_node
  public_status
  progress_message
  retryable
  safe_error
  terminal
  tool_call_count

trace:
  redacted_node_events
  redacted_tool_calls
  dependency_events
```

## Contract Additions

Add only the contracts needed for v2 behavior:

- `ImageSafetyResult`: explicit unsafe/NSFW/disallowed screening output.
- `TextSafetyResult`: explicit safety and instruction-injection screening for text-only descriptions and image focus notes.
- `ProductDiscoveryProfile`: product family, refined product type, consumer decision factors, important details, recommended engines, engine rationale, ranking priorities, and uncertainty.
- `ProductSearchContext`: exact/broad terms, feature/material/style terms, exclusions, must-have details, and optional details.
- `ProductSearchPlan`: bounded source engine/search plan with validated params.
- `ProductSearchExecutionResult`: raw provider result wrappers and source-level errors for normalization.
- `RankingScoreBreakdown`: component scores for product type, visual attributes, features, style/material/color, price preference, source confidence, availability, mismatch penalty, and final score.
- `CandidateMismatch`: structured mismatch flags and caveats.

Existing contracts that should remain app-facing unless a later spec changes them:

- `ImageGateResult`
- `ProductReference`
- `SourceProduct`
- `RankedProduct`
- `ProductResearchBrief`
- `WorkflowProviderError`

## Failure Behavior

| Failure | Result |
| --- | --- |
| Unsafe/NSFW image | Stop before extraction. Persist `failed`, non-retryable, safe code `unsafe_image`. |
| Unsafe text | Stop before extraction. Persist `failed`, non-retryable, safe code `unsafe_text`. |
| Regulated or dangerous product category | Stop before source research. Persist `failed`, non-retryable, safe code `regulated_product`. |
| Prompt-injected text or focus note | Persist `needs_refinement` with safe code `text_prompt_injection`; do not extract or search. |
| Malformed or low-signal text | Persist `needs_refinement` with safe code `text_input_unclear`; do not extract or search. |
| Non-product assistant/link request | Persist `needs_refinement` with safe code `text_not_product`; do not extract or search. |
| Safety unclear | Request refinement before product gate/extraction. Preserve the user-safe safety message when available. |
| Text safety model unavailable | Fall back to deterministic central-policy screening; do not expose raw provider errors to the user. |
| Text safety model returns low-confidence safe result | Treat as `unclear` and request refinement instead of searching. |
| Safety model uses `unsafe` for product clarity instead of disallowed content | Normalize to `unclear` unless `unsafeReasons` contains a recognized disallowed safety category. |
| Non-product image | Persist `needs_refinement` with safe guidance. |
| Extracted reference is not a searchable product | Persist `needs_refinement` with safe code `text_not_product`; do not run discovery or source search. |
| Multiple products without target | Persist `needs_refinement` with optional target-text guidance. |
| Image instruction/prompt-injection risk | Treat text as untrusted evidence; fail or refine if risk is high. |
| Extraction provider unavailable before reference | Persist retryable `failed`. |
| Invalid extraction output | Run one repair pass; fail safely if still invalid. |
| Product profile planning unavailable | Use deterministic fallback profile when possible; otherwise persist `partial` after reference. |
| Search planning unavailable | Use deterministic Google Shopping fallback plan when possible; otherwise persist `partial` after reference. |
| Research unavailable after reference | Persist `partial` brief with product reference and safe source-unavailable message. |
| No source results | Complete with no verified match and clear refinement guidance. |
| Generic source links without product evidence | Drop during discovery normalization; do not render product cards for them. |
| Ranking server/model unavailable | Use deterministic fallback ranking if source products exist. |
| Worker crash | Use existing safe `worker_task_failed` behavior. |

## Non-Functional Requirements

- V2 is the only production workflow after implementation.
- The app must remain runnable through Docker Compose after each module lands.
- MCP tool invocation must be allowlisted, bounded, timeout-protected, retry-protected, circuit-breaker-aware, and secret-redacted.
- Graph execution must preserve partial results when later nodes fail.
- User-facing output must never include raw provider errors, raw provider payloads, raw image bytes, or secret-bearing URLs.
- Ranking explanations must be traceable to provided reference/context/source data.
- Tests should mock live AI and paid providers by default.
- Optional live smoke checks must remain explicitly gated by environment configuration.

## Acceptance Criteria

- A text-only job reaches a final source-backed brief through the V2 graph.
- Text-only unsafe, prompt-injected, malformed, or non-product requests stop before extraction and source research.
- Text-only regulated or dangerous product requests stop before extraction and source research.
- Text safety model classification can block long-tail regulated/unsafe categories when deterministic rules do not match.
- Low-confidence safe model classifications produce refinement instead of source research.
- Extracted non-product references such as lists, countries, facts, or general knowledge requests stop before discovery/source research.
- Image-derived regulated or dangerous product references stop before discovery and source research.
- Image plus optional target text screens the text before image extraction uses the focus note.
- An image job runs `screen_image_safety` before product gate or extraction.
- Unsafe image input stops before extraction and source research.
- Ambiguous multi-product input returns `needs_refinement` instead of guessing.
- Image plus optional target text can select the intended product path.
- The bounded product-understanding loop exposes only gate, disambiguation, and extraction tools to the model.
- The bounded product-understanding loop enforces its tool-call budget and validates the final decision contract.
- Extraction output validation performs at most one repair pass.
- Product discovery produces a `ProductDiscoveryProfile` that guides search and later ranking.
- Product discovery search planning selects only allowed engines and respects the configured call budget.
- Product discovery planning runs distinct closest-match and similar-alternatives searches when call budget allows.
- Product discovery executes SerpAPI MCP calls only through validated code-driven search plans.
- Product discovery normalizes provider results to `SourceProduct[]`.
- Product discovery filters generic organic/link-only results that do not have product-shaped evidence before creating product cards.
- Research source failure after reference extraction produces a partial result.
- Ranking uses score breakdowns and mismatch flags when available.
- Ranking server/model failure falls back to deterministic ranking.
- MCP runtime blocks non-allowlisted tools.
- Downstream provider failures inside a reachable MCP service preserve their provider/tool error code and do not mark the MCP service itself as unavailable.
- MCP servers log redacted tool/provider failures with enough context to identify the failing stage, downstream dependency, and operation.
- Provider failures map to safe user-facing error codes.
- Secrets and secret-bearing MCP URLs are redacted from logs and trace records.
- Frontend polling continues to receive supported public statuses and brief shapes.

## Out of Scope

- User accounts, saved history, price alerts, checkout, or purchasing.
- Long-lived V1/V2 workflow feature flag.
- Giving model-callable tools direct database or object-storage write access.
- Unbounded autonomous agent loops.
- Full source marketplace expansion beyond the first production source boundary.
- Dedicated vector memory unless a later product spec requires it.
