# Technical Design: ThriftLens

Status: Draft for review

Source PRD: `specs/product-prd/PRD.md`

## 1. Design Goals

ThriftLens should be a deployable product research workbench that supports two first-class entry points:

- Image input: user uploads a product image and gets a structured product reference plus source-backed matches.
- Text input: user describes a product idea and gets a structured product reference, optional visual reference, and source-backed matches.

The core technical bet is to make the structured product reference the durable internal artifact. Raw images are temporary inputs for the vision step; downstream agents should use structured data.

## 2. AI Workflow Boundary

V1 uses a two-stage model workflow:

1. Extraction: image or text input is converted into a validated `ProductReference`.
2. Grounded synthesis: researched `SourceProduct` results are ranked and explained against the `ProductReference`.

The research client is the factual boundary. Product names, prices, retailers, availability, source URLs, and freshness data must come from source results, not model invention.

Recommended split:

- Model-assisted: image perception, text-to-reference extraction, search query generation, concise match reasoning, uncertainty wording, and recommendation labels when source coverage supports them.
- Deterministic/service logic: schema validation, source querying, source result normalization, exact price extraction from source data, verified vs possible match separation, price-range calculation, error states, and final response shape.
- Hybrid scoring: deterministic scoring should produce an initial ranking; model assistance may explain or lightly refine ranking using only provided `ProductReference` and `SourceProduct` data.

This design gives the product meaningful AI behavior while keeping pricing and product claims source-grounded.

## 3. Architecture Overview

Proposed high-level flow:

```txt
UI workbench
  -> API research job endpoint
  -> persistent job record
  -> background task queue
  -> workflow worker
  -> orchestration graph / workflow controller
     -> input normalizer
     -> temporary image storage, only for image input
     -> MCP-style multi-server tool client
          image input -> vision/image server tool -> ProductReference
          text input  -> text extraction/model tool -> ProductReference
     -> optional clarification or repair
     -> MCP-style multi-server tool client
          shopping/search research server tools
          retailer/source research server tools
     -> result normalization
     -> ranking/recommendation
     -> ProductResearchBrief
  -> job state and final result
  -> UI polling result cards
```

Recommended V1 implementation shape:

- Use a real graph-style workflow orchestrator, such as LangGraph, to coordinate extraction, research, ranking, and error handling.
- Treat vision extraction and product research as real tool/server capabilities exposed behind an MCP-style multi-server client boundary, not as dummy placeholders.
- Keep UI, workflow orchestration, tool clients, validation, source normalization, and ranking in separate modules.
- Keep source/tool contracts stable so individual servers or adapters can change without rewriting the product flow.
- Keep raw image handling isolated from downstream agent logic.
- Build the V1 architecture as production-shaped software even if the first source/server set is narrow.
- Run research workflows as queue-backed background jobs so slow AI/tool calls do not block web requests.
- Use frontend polling against job status endpoints for progress, partial results, retry, and refresh recovery.

### Orchestration Model

The workflow controller should behave like a bounded graph, not an open-ended autonomous agent. The graph owns state, decides which tool to call next, validates outputs between nodes, and returns explicit statuses to the UI.

Proposed graph nodes:

1. `normalizeInput`: validate image/text input and preferences.
2. `prepareImage`: store image temporarily when image input is present.
3. `extractReference`: call the vision server for images or text extraction tool for descriptions.
4. `validateReference`: validate/repair `ProductReference`.
5. `researchProducts`: call one or more research server tools through the MCP-style client.
6. `normalizeSources`: convert source responses into `ResearchSourceResult` and `SourceProduct`.
7. `rankProducts`: deterministic scoring, grouping, and optional model-assisted reranking/explanation.
8. `buildBrief`: assemble `ProductResearchBrief`.

The graph should support partial completion. For example, if research fails after reference extraction, return the product reference with `research_unavailable` instead of losing the whole workflow.

### Workflow Execution Model

V1 should use queue-backed async execution with polling from the UI.

Request flow:

1. `POST /api/research-jobs` validates the request, stores the uploaded image when needed, creates a durable job record, enqueues a background task, and returns `jobId`.
2. A worker process runs the LangGraph-style workflow, calls MCP servers through the multi-server client, and updates the job record after each major stage.
3. `GET /api/research-jobs/:id` returns the current job status, progress stage, safe user-facing message, partial result, and final result when available.
4. Optional retry actions reuse the durable `ProductReference` when available so the user does not need to start over after a research-source failure.

This is a production architecture decision. Product research depends on slow and variable external systems: model calls, vision extraction, search APIs, retailer sources, retries, and partial failures. A task queue keeps web requests short, lets workers scale independently, supports retries and timeouts, and makes progress observable. Polling remains the simplest V1 browser mechanism for displaying that job state.

Proposed job statuses:

```ts
type ResearchJobStatus =
  | "queued"
  | "extracting_reference"
  | "needs_refinement"
  | "researching_sources"
  | "ranking_results"
  | "complete"
  | "partial"
  | "failed"
  | "expired";

type ResearchJob = {
  id: string;
  status: ResearchJobStatus;
  inputType: "image" | "text";
  progressMessage: string;
  productReference?: ProductReference;
  partialBrief?: ProductResearchBrief;
  finalBrief?: ProductResearchBrief;
  retryable: boolean;
  error?: {
    code: string;
    userSafeMessage: string;
  };
  createdAt: string;
  updatedAt: string;
  expiresAt: string;
};
```

Execution requirements:

- Web API requests should not wait for the full research workflow to finish.
- Workers should enforce per-stage timeouts and bounded retries for retryable provider/source failures.
- Job state should be durable enough to survive a browser refresh and return partial results.
- The UI should poll at a bounded interval and stop when the job reaches a terminal status.
- Queue workers should be horizontally scalable without changing the user-facing API.
- Job records and temporary image files should expire after a configured TTL.
- If the queue or worker is unavailable, the API should return a clear service-unavailable state rather than pretending to research.

### Tool Server Boundaries

Vision/image server:

- Input: temporary image reference or uploaded image payload.
- Output: structured `ProductReference`.
- Responsibility: perception only. It should not call research sources or rank products.

Text extraction/model tool:

- Input: user text description.
- Output: structured `ProductReference` or clarification request.
- Responsibility: turn text into the same durable reference contract used by image input.

Research server/tools:

- Input: `ProductReference`, generated queries, and user preferences.
- Output: `ResearchSourceResult[]`.
- Responsibility: source access and normalization, not final ranking.

Ranking/explanation component:

- Input: `ProductReference`, `SourceProduct[]`, preferences, and source completeness.
- Output: `RankedProductResult[]`, grouped alternatives, confidence, and explanation.
- Responsibility: deterministic baseline ranking plus constrained model-assisted explanation/reranking.

## 4. Runtime Components

### Product Workbench UI

Responsibilities:

- Accept image upload or text description.
- Accept optional preferences: ranking mode, price/budget, location/source if supported.
- Show product reference, research progress, verified matches, possible matches, grouped alternatives, trust signals, and errors.
- Let user edit/refine the reference or preferences and rerun research.
- Support copy/share of the research brief and opening product/source links.

### Orchestration Graph / Workflow Controller

Responsibilities:

- Accept a single product research request.
- Decide whether the input path is image or text.
- Coordinate extraction, validation, research, ranking, and response shaping as bounded graph nodes.
- Call tool servers through the MCP-style multi-server client.
- Preserve partial results when later stages fail.
- Return explicit status states rather than raw provider errors.
- Prevent open-ended tool use; only allowed graph transitions should run.

### MCP-Style Multi-Server Client

Responsibilities:

- Provide one client interface for calling multiple capability servers/tools.
- Route image extraction requests to the vision/image server.
- Route text reference extraction requests to the text/model tool.
- Route product research requests to shopping/search or retailer/source tools.
- Normalize tool errors into structured internal errors.
- Hide transport/provider details from the workflow graph.

### Tool Execution Policy

Responsibilities:

- Wrap all MCP/tool calls with consistent timeout, retry, circuit-breaker, and error-normalization behavior.
- Keep dependency health policy separate from product workflow logic.
- Return structured tool outcomes to the workflow graph instead of throwing raw provider errors through the system.
- Prevent unhealthy dependencies from consuming worker capacity when they are already failing.

This layer should sit between the workflow graph and the MCP-style multi-server client:

```txt
Workflow graph
  -> Tool execution policy
     -> timeout
     -> bounded retry
     -> circuit breaker check
     -> structured error normalization
  -> MCP-style multi-server client
  -> capability servers/tools
```

The workflow graph decides what the failure means for the product experience. The policy layer decides whether a tool call should be attempted, retried, skipped, or marked as unavailable.

### Temporary Image Store

Responsibilities:

- Store uploaded images only long enough to run vision extraction and support retry.
- Enforce TTL deletion or workflow-completion deletion.
- Avoid logging raw image contents or long-lived public URLs.
- Return a recoverable error if the image expires before vision extraction can rerun.

V1 storage choice is still open: in-memory/temp filesystem vs object storage. The technical spec should pick the simplest reliable option for the chosen stack.

### Product Reference Extractor Tool Boundary

Responsibilities:

- For image input, call the vision model/server.
- For text input, call a text model to produce the same `ProductReference` shape.
- Ask targeted clarification only if text input is too ambiguous to produce a useful reference.
- Validate and repair structured output before research begins.

### Research Tool Boundary

Responsibilities:

- Convert a `ProductReference` and user preferences into source queries.
- Query configured research sources.
- Normalize results into a common `SourceProduct` shape.
- Report per-source errors without failing the entire workflow when possible.

V1 should keep this layer source-agnostic. The concrete source choice belongs in technical design review, but the integration should use the same MCP/HTTP tool boundary planned for production. The first source set can be narrow, but it should not be hidden behind throwaway local-only plumbing.

### Ranking and Recommendation Engine

Responsibilities:

- Separate verified matches from possible matches.
- Lead with the closest verified match.
- Group alternatives into cheaper, similar-price, and premium sections when enough data exists.
- Add recommendation labels only when confidence and source coverage support them.
- Produce match reasoning and confidence labels.
- Use deterministic scoring as the baseline and restrict any model-assisted explanation/ranking to the provided product reference and source-backed product results.

V1 ranking policy:

- Start with deterministic scoring for every `SourceProduct`.
- Use model assistance only after deterministic scoring has selected a bounded candidate set.
- If model-assisted reranking/explanation fails, fall back to deterministic ranking and deterministic match reasons.
- The model may not introduce new products, prices, retailers, source URLs, or availability.
- The model may only choose among provided candidates, explain tradeoffs, and assign supported recommendation labels.

Baseline deterministic scoring signals:

- Product type/category alignment
- Brand/model match when evidence exists
- Must-have feature overlap
- Observed attribute overlap
- Color/material/style overlap
- User preference fit, including budget and ranking preference
- Source-backed price availability
- Source count or source reliability
- Missing required feature penalties
- Different product type penalties

## 5. Core Data Contracts

### ProductReference

Produced by vision/text extraction and used by research/ranking.

```ts
type Confidence = "high" | "medium" | "low";
type EvidenceLevel = "observed" | "inferred" | "user_provided";

type EvidenceField<T> = {
  value: T;
  confidence: Confidence;
  evidence: EvidenceLevel;
  notes?: string;
};

type ProductReference = {
  inputType: "image" | "text";
  referenceType: "user_provided" | "generated" | "structured_text";
  productType: EvidenceField<string>;
  shortDescription: string;
  brand?: EvidenceField<string>;
  model?: EvidenceField<string>;
  useCase?: EvidenceField<string>;
  observedAttributes: string[];
  inferredAttributes: string[];
  mustHaveFeatures: string[];
  styleTags: string[];
  colors: string[];
  materials: string[];
  notableFeatures: string[];
  constraints: string[];
  searchQueries: string[];
  confidence: Confidence;
  missingInfo: string[];
  warnings: string[];
};
```

Rules:

- `productType`, `shortDescription`, `searchQueries`, and `confidence` are required.
- Empty arrays are allowed for unknown optional details.
- Generated references must never be presented as purchasable products.
- Observed facts, inferred attributes, and user-provided details must stay distinguishable.
- Brand/model fields should only be populated when there is evidence; low-confidence guesses belong in warnings or missing-info notes instead of being treated as facts.
- Search query generation should prioritize `productType`, `mustHaveFeatures`, and `observedAttributes` before weaker inferred style terms.

### ResearchPreferences

```ts
type RankingPreference =
  | "closest_match"
  | "best_value"
  | "cheapest"
  | "similar_price"
  | "premium";

type ResearchPreferences = {
  rankingPreference?: RankingPreference;
  minPrice?: number;
  maxPrice?: number;
  currency?: string;
  location?: string;
  preferredSources?: string[];
};
```

### SourceProduct

Normalized product result from any research source.

```ts
type SourceProduct = {
  id: string;
  title: string;
  sourceName: string;
  sourceUrl: string;
  imageUrl?: string;
  price?: number;
  currency?: string;
  availability?: string;
  observedAt?: string;
  extractedAttributes: string[];
  rawSnippet?: string;
  metadata?: {
    sourceRank?: number;
    isSponsored?: boolean;
    shippingSummary?: string;
    rating?: number;
    reviewCount?: number;
  };
};
```

Rules:

- Exact prices must come from a source result.
- Missing price should be represented as unknown, not estimated.
- Each research source must normalize its response into this common shape before ranking or UI rendering.
- Do not return arbitrary raw source payloads to the UI or downstream model steps.
- Keep only safe, useful source-specific details in `metadata`.
- Full raw source responses may be used transiently inside an adapter for normalization, but should not become part of the product contract.

### ResearchSourceResult

Internal result returned by each source adapter.

```ts
type ResearchSourceErrorCode =
  | "TIMEOUT"
  | "RATE_LIMITED"
  | "UNAVAILABLE"
  | "INVALID_RESPONSE"
  | "AUTH_REQUIRED"
  | "UNKNOWN";

type ResearchSourceResult = {
  sourceName: string;
  products: SourceProduct[];
  error?: {
    code: ResearchSourceErrorCode;
    message: string;
    retryable: boolean;
  };
};
```

Rules:

- Source adapter errors should be structured internally for observability, retries, and partial-failure handling.
- Raw provider error messages should not be shown directly to users.
- The UI should receive only a safe research completeness summary.

### RankedProductResult

```ts
type ResultGroup =
  | "best_match"
  | "cheaper"
  | "similar_price"
  | "premium"
  | "possible_match";

type RecommendationLabel =
  | "best_overall"
  | "best_match"
  | "best_value"
  | "cheapest"
  | "premium_pick";

type RankedProductResult = {
  product: SourceProduct;
  group: ResultGroup;
  deterministicScore: number;
  confidence: Confidence;
  matchReason: string;
  recommendationLabels: RecommendationLabel[];
  caveats: string[];
};
```

### ProductResearchBrief

```ts
type ProductResearchBrief = {
  status:
    | "complete"
    | "partial"
    | "needs_refinement"
    | "no_verified_match"
    | "research_unavailable"
    | "error";
  productReference: ProductReference;
  verifiedMatches: RankedProductResult[];
  possibleMatches: RankedProductResult[];
  priceContext: {
    exactPrices: SourceProduct[];
    observedRange?: {
      min: number;
      max: number;
      currency: string;
      sourceCount: number;
    };
  };
  groupedAlternatives: {
    cheaper: RankedProductResult[];
    similarPrice: RankedProductResult[];
    premium: RankedProductResult[];
  };
  trustSummary: {
    sourceCount: number;
    attemptedSourceCount: number;
    unavailableSourceCount: number;
    completeness: "complete" | "partial" | "unavailable";
    userSafeMessage?: string;
    freshnessNotes: string[];
    uncertaintyNotes: string[];
  };
  userActions: {
    canRefine: boolean;
    canRetry: boolean;
    canCopy: boolean;
  };
};
```

## 6. AI Workflow

### Step 1: Perceive

Image path:

- Upload image.
- Store temporarily.
- Send image to vision server/model.
- Return structured `ProductReference`.

Text path:

- Send text description to text model.
- Return structured `ProductReference`.
- If too vague, return targeted clarification questions instead of guessing.

### Step 2: Validate and Repair

- Validate model output against the `ProductReference` schema.
- Attempt one repair pass for malformed structured output.
- If still invalid, return a recoverable extraction error.

### Step 3: Research

- Generate source queries from `ProductReference.searchQueries` plus key attributes.
- Query the research client layer.
- Normalize source results to `SourceProduct`.
- Preserve source-level failures.

### Step 4: Rank and Explain

- Score products using attribute overlap, category alignment, visual/text similarity signals, price relevance, and source reliability.
- Produce a deterministic score and baseline group for every normalized product.
- Pass only a bounded candidate set to the model-assisted reranking/explanation step.
- Use model output only to refine close calls, explain tradeoffs, and assign recommendation labels from source-backed data.
- Separate verified matches from possible matches.
- Create grouped alternatives when there is enough source-backed price data.
- Generate concise match reasoning and caveats.

### Step 5: Respond

- Return the `ProductResearchBrief`.
- Include partial results if later steps fail.
- Avoid unsupported product, price, retailer, or availability claims.

## 7. Reliability and Failure Handling

Required failure modes:

- Empty input: return validation error before model call.
- Low-quality image: preserve upload state and ask for clearer image or text.
- Ambiguous text: ask targeted clarification questions.
- Vision server unavailable: preserve input if possible and allow retry.
- Research unavailable: return product reference plus `research_unavailable` status.
- Source dependency degraded: return partial results and mark unavailable sections.
- No verified match: show product reference and possible matches/refinement guidance.
- Invalid model output: repair once, then show recoverable error.
- Temporary image expired: preserve product reference if available; otherwise request re-upload.

### Failure Semantics

Failures should be scoped to the smallest recoverable part of the workflow.

- Input validation failure: do not create a runnable research job.
- Vision/text extraction failure: mark the job `failed` or `needs_refinement` because no reliable `ProductReference` exists.
- Single research source failure: continue with other sources and mark the brief `partial`.
- All research sources unavailable: return the product reference with `research_unavailable` when extraction succeeded.
- Ranking/explanation model failure: fall back to deterministic ranking and deterministic match reasons.
- Queue or worker unavailable: return a service-unavailable state before pretending the job has started.

The user should never receive fabricated fallback products, prices, retailers, or availability. Reduced capability should be explicit.

### Retry Policy

Retries should be bounded, stage-specific, and observable.

Retryable:

- Network timeout.
- Provider 5xx.
- Temporary rate limit after a safe backoff.
- Transient MCP transport/session failure.
- Malformed model structured output when one repair pass can be attempted.

Not retryable:

- Invalid user input.
- Unsupported file type.
- Missing or invalid API key.
- Image too blurry to extract useful facts.
- Valid but low-confidence extraction.
- Source-backed no-product-found result.

Every retry should record non-sensitive attempt metadata:

```ts
type JobAttempt = {
  stage: "extract_reference" | "research_source" | "rank_results";
  dependency: string;
  attempt: number;
  errorCode: string;
  retryable: boolean;
  startedAt: string;
  finishedAt?: string;
};
```

Recommended V1 policy:

- Use short bounded backoff for retryable failures.
- Cap retries per stage/dependency.
- Preserve partial results before retrying later sources.
- Surface only safe summaries to users, such as "Some sources are temporarily unavailable."

### Circuit Breakers

Circuit breakers protect the app when a dependency is repeatedly unhealthy. They should be tracked per dependency, not globally.

```ts
type DependencyHealthState = "closed" | "open" | "half_open";

type DependencyHealth = {
  dependency: "vision_server" | "text_extraction" | "shopping_search" | "retailer_source" | "ranking_model";
  state: DependencyHealthState;
  recentFailureCount: number;
  recentSuccessCount: number;
  openedAt?: string;
  cooldownUntil?: string;
};
```

State behavior:

- `closed`: normal calls are allowed.
- `open`: calls are skipped for a cooldown window and returned as structured dependency-unavailable outcomes.
- `half_open`: allow limited test calls to determine whether the dependency recovered.

Expected degradation:

- Vision server open: image jobs cannot extract a reference; text jobs can still run.
- Text extraction open: text jobs cannot extract a reference; image jobs can still run.
- Shopping/search open: use retailer/source tools if available and mark research completeness as partial.
- One retailer source open: exclude that source and continue with other sources.
- Ranking model open: use deterministic ranking and deterministic explanations.

Tool-call failures should normalize to a structured result, for example:

```ts
type ToolExecutionErrorCode =
  | "TIMEOUT"
  | "RATE_LIMITED"
  | "CIRCUIT_OPEN"
  | "UNAVAILABLE"
  | "INVALID_RESPONSE"
  | "AUTH_REQUIRED"
  | "UNKNOWN";

type ToolExecutionError = {
  dependency: string;
  code: ToolExecutionErrorCode;
  retryable: boolean;
  userSafeMessage: string;
};
```

Raw provider errors stay internal. The workflow graph consumes structured errors and decides whether the job becomes `partial`, `failed`, `needs_refinement`, or `research_unavailable`.

## 8. Non-Functional Design

Scalability:

- Keep extraction, research, and ranking as separable modules.
- Keep research sources behind adapter interfaces.
- Run slow AI/research work in queue workers that can scale independently of web requests.
- Use circuit breakers to avoid flooding unhealthy dependencies under load.
- Avoid long-lived raw-image persistence.

Low latency:

- Avoid extra model calls where deterministic validation is enough.
- Query independent research sources in parallel when supported.
- Start with structured reference extraction before optional visual generation.
- Show progress states for extraction, research, and ranking.
- Return `jobId` quickly and let the UI poll instead of keeping long web requests open.

Availability:

- Degrade from full research brief to partial brief.
- Distinguish provider/server failures from no-match outcomes.
- Allow retry without losing user input or the structured reference.
- Isolate dependency failures with the tool execution policy so one failing source does not take down the whole workflow.

Security/privacy:

- Never log `.env` values, provider keys, raw image payloads, or private source responses.
- Delete temporary images after TTL/workflow completion.
- Treat generated product references as non-purchasable search anchors.

## 9. Testing Strategy

Unit tests:

- Product reference schema validation.
- Model-output repair/failure handling.
- Research result normalization.
- Ranking group assignment.
- Price-context calculation.
- Verified vs possible match separation.

Integration tests:

- Image workflow with mocked vision response.
- Text workflow with mocked extraction response.
- Research unavailable path.
- Partial source failure path.
- Missing API key/sample-mode path.

UI or smoke tests:

- Empty state.
- Loading/progress states.
- Complete result state.
- No verified match state.
- Possible matches only state.
- Copy/share and source-link actions.

## 10. Implementation Questions

These should be answered before the Software Engineer phase:

1. What application stack should V1 use?
2. What AI provider/model handles image-to-reference extraction?
3. What AI provider/model handles text-to-reference extraction and ranking explanations?
4. Does V1 include actual generated reference images, or only structured references?
5. What concrete research client/server source should V1 use first?
6. Where should temporary images live, and what TTL should be enforced?
7. Which task queue/store should V1 use for background research jobs?
8. What sample-mode data should be included for missing keys/unavailable providers?

## 11. Proposed Build Phases

1. Choose stack, providers, and research source.
2. Implement schema/types and validation.
3. Build mocked workflow end-to-end with sample data.
4. Add image upload and temporary image handling.
5. Add vision/text extraction adapters.
6. Add research client adapter.
7. Add ranking/recommendation.
8. Build workbench UI states.
9. Add tests for acceptance criteria.
10. Run cleanup/review passes.
