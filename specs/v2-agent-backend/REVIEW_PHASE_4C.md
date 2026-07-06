# V2 Agent Backend Review: Phase 4C

## Spec Compliance

- Added bounded ReAct-style product understanding after image safety and before reference persistence.
- Kept LangGraph in control of stage routing and terminal states.
- Exposed only `image_product_gate`, `disambiguate_target_product`, and `extract_product_reference` to the model loop.
- Preserved deterministic policy flow as the fallback when the ReAct loop is disabled or unavailable.

## Acceptance Criteria Coverage

- Tool allowlist and call budget are implemented in `ProductUnderstandingAgent`.
- Final model output is validated as `ProductUnderstandingDecision`.
- New unit coverage verifies tool binding, tool execution order, final decision validation, and budget enforcement.
- Existing graph tests still cover unsafe images, ambiguous images, image plus target text, text-only extraction, and stored-reference reuse.

## Gaps

- Live ReAct execution requires rebuilding the backend image with `langchain-google-genai`.
- The loop is intentionally opt-in through `PRODUCT_UNDERSTANDING_AGENT_ENABLED` to avoid test/sample quota spend.
- Context, research, and ranking MCP capability phases are not covered by this review.

## Result

Approved for this phase.
