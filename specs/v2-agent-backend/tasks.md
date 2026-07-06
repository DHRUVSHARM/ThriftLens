# V2 Agent Backend Tasks

Status: Draft implementation sequence

## Phase 1: Spec and Contracts

- [ ] Approve `specs/v2-agent-backend/SPEC.md`.
- [x] Add v2 graph state and MCP contract types.
- [x] Extend tests for contract validation.

## Phase 2: Agent Runner and Graph Shell

- [x] Add `AgentJobRunner`.
- [x] Add LangGraph graph construction.
- [x] Update Celery worker to invoke the final runner.
- [x] Keep FastAPI gateway and polling response shapes stable.

## Phase 3: Shared MCP Runtime

- [x] Add multi-server MCP client factory.
- [x] Add tool discovery and namespacing.
- [x] Add explicit tool allowlist.
- [x] Wrap tool calls with timeout, retry, circuit breaker, and redacted trace logging.

## Phase 4: Extraction MCP Capability

- [x] Implement `extraction.screen_image_safety`.
- [x] Implement `extraction.image_product_gate`.
- [x] Implement `extraction.extract_product_reference`.
- [x] Implement `extraction.repair_product_reference`.
- [x] Implement `extraction.disambiguate_target_product`.
- [x] Add tests for unsafe, non-product, ambiguous, image+target, text-only, and repair flows.
- [x] Run extraction MCP server as a configurable service.
- [x] Register extraction MCP tools through the shared runtime.
- [x] Wire LangGraph safety, gate, extraction, and reference persistence nodes to extraction tools.
- [x] Ensure downstream research reuses graph-persisted product references without duplicate extraction.
- [x] Replace fixed post-safety image gate/extract sequence with bounded product-understanding node.
- [x] Add opt-in ReAct-style tool binding for bounded product understanding.
- [x] Enforce allowlisted gate/disambiguation/extraction tools and tool-call budget.

## Phase 5: Product Discovery MCP Capability

- [x] Add `ProductDiscoveryProfile`, `ProductSearchContext`, `ProductSearchPlan`, and discovery execution contracts.
- [x] Implement `discovery.classify_product_profile`.
- [x] Implement `discovery.build_search_context`.
- [x] Implement `discovery.plan_search_sources`.
- [x] Implement `discovery.execute_search_plan`.
- [x] Implement `discovery.normalize_products`.
- [x] Add optional `discovery.verify_source`.
- [x] Move SerpAPI calls behind the Product Discovery MCP boundary.
- [x] Wire LangGraph discovery nodes after reference persistence and before ranking.
- [x] Enforce engine allowlist, allowed params, and configured call budget.
- [x] Add source failure, invalid plan, call budget, normalization, and partial-result tests.

## Phase 6: Ranking MCP Capability

- [x] Add hybrid ranking score breakdowns.
- [x] Add mismatch detection.
- [x] Add user-facing grouping.
- [x] Add source-grounded explanations.
- [x] Preserve deterministic fallback.

## Phase 7: Traceability, Cleanup, and Review

- [x] Persist redacted graph/tool events.
- [x] Update `.env.example`, README, and APPROACH as environment/runtime changes land.
- [x] Run relevant tests after each phase.
- [x] Run `skills/code-structure-cleanup/SKILL.md` after each working feature phase.
- [x] Produce Review Agent report before marking each phase complete.
