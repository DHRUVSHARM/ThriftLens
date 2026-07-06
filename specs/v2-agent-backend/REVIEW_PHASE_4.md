# Review: V2 Agent Backend Phase 4

## Spec Compliance

- Implemented the Product Extraction MCP capability boundary from `SPEC.md`.
- Added server-facing tools for image safety screening, image product gating, product reference extraction, product reference repair, and target product disambiguation.
- Kept provider-specific Gemini/sample behavior behind provider clients; MCP tools expose validated ThriftLens contracts.

## Acceptance Criteria Coverage

- `extraction.screen_image_safety`: covered by safe and unsafe mapping tests.
- `extraction.image_product_gate`: covered by alias/schema payload test.
- `extraction.extract_product_reference`: covered by text extraction payload test.
- `extraction.repair_product_reference`: covered by repair payload test.
- `extraction.disambiguate_target_product`: covered by target-selection and ambiguous-refinement tests.

## Gaps

- The LangGraph workflow does not invoke this extraction server yet; this phase only establishes the server/tool boundary.
- The current safety tool maps through the existing image gate provider call because the provider does not yet expose a dedicated safety-only model call.

## Verification

- `docker compose run --rm api python -m pytest tests/test_extraction_mcp_tools.py tests/test_v2_agent_contracts.py tests/test_mcp_runtime.py tests/test_provider_integrations.py`
- `python3 -m py_compile backend/app/workflow_contracts.py backend/app/mcp_servers/extraction/tools.py backend/app/mcp_servers/extraction/server.py backend/tests/test_extraction_mcp_tools.py`

## Review Result

Approved for this phase. The extraction MCP capability is ready for code review and later graph wiring.
