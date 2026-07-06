# Review: V2 Agent Backend Phase 4B

## Spec Compliance

- Connected the Product Extraction MCP capability to the shared runtime and LangGraph shell.
- Added a configurable `extraction-mcp` service using FastMCP over streamable HTTP.
- Added an extraction MCP client that allowlists and validates extraction tool outputs.
- LangGraph now owns safety screening, image gate, extraction, product-reference persistence, and terminal unsafe/refinement decisions.
- Downstream research/ranking reuses an already persisted `ProductReference`, avoiding duplicate extraction calls.
- Image safety now uses a dedicated provider method and `ImageSafetyResult` schema before product gate, including NSFW/unsafe categories and user-safe messaging.
- Post-safety image understanding now runs through a bounded product-understanding node with only three allowed tool steps: product gate, optional target disambiguation, and extraction.

## Acceptance Criteria Coverage

- Text-only graph flow extracts a `ProductReference`, stores it, and invokes downstream workflow.
- Image graph flow performs safety, gate, extraction, persistence, and downstream handoff.
- Unsafe image fails before gate, extraction, or downstream workflow.
- Unsafe image failure preserves the safety tool's user-safe message instead of exposing raw provider details.
- Ambiguous multi-product image requests refinement before extraction.
- Multi-product image with target text can disambiguate the intended product and continue to extraction.
- Existing worker orchestration behavior remains covered.
- Extraction MCP client covers adapter-wrapped text content results from FastMCP.

## Gaps

- Context, research, and ranking are still handled by the existing workflow path until their MCP servers are carved out.
- The extraction service has `service_started` dependency in Compose, not a full healthcheck.

## Verification

- `docker compose config`
- Real FastMCP stdio smoke through `MCPRuntime` in `SAMPLE_MODE`
- `docker compose run --rm api python -m pytest tests/test_v2_agent_runner.py tests/test_extraction_mcp_tools.py tests/test_mcp_runtime.py tests/test_worker_orchestration.py tests/test_provider_integrations.py`
- `docker compose run --rm api python -m pytest tests/test_extraction_mcp_tools.py tests/test_provider_integrations.py tests/test_v2_agent_runner.py tests/test_worker_orchestration.py`
- `docker compose run --rm api python -m pytest tests/test_v2_agent_runner.py tests/test_extraction_mcp_tools.py tests/test_provider_integrations.py tests/test_worker_orchestration.py`
- `python3 -m py_compile backend/app/agent/graph.py backend/app/agent/runner.py backend/app/mcp_servers/extraction/client.py backend/app/mcp_servers/extraction/server.py backend/app/workflow.py backend/app/config.py backend/tests/test_v2_agent_runner.py backend/tests/test_extraction_mcp_tools.py`
- `python3 -m py_compile backend/app/gemini_provider.py backend/app/sample_providers.py backend/app/mcp_servers/extraction/tools.py backend/app/agent/graph.py backend/tests/test_extraction_mcp_tools.py backend/tests/test_provider_integrations.py backend/tests/test_v2_agent_runner.py`
- `python3 -m py_compile backend/app/agent/product_understanding.py backend/app/agent/graph.py backend/app/workflow_contracts.py backend/tests/test_v2_agent_runner.py`

## Review Result

Approved for this phase. The extraction MCP server is now connected to the runtime and graph-driven job path.
