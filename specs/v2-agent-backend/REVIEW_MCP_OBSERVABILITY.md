# Review: MCP Observability Boundary

## Spec Compliance

- Added a shared structured MCP tool-error envelope so downstream provider failures inside reachable MCP services can be returned as safe structured tool results.
- Updated extraction and discovery MCP clients to decode that envelope and re-raise `WorkflowProviderError` with preserved code, retryability, dependency, operation, and origin code.
- Wrapped provider-backed extraction and discovery MCP server tools with shared observability handling.
- Configured secret-redaction logging inside extraction, discovery, and ranking MCP server processes.
- Added provider-policy warning logs with dependency, operation, safe code, retryability, attempt count, and exception class.
- Avoided traceback logging for unexpected MCP tool failures to reduce secret/payload leakage risk.
- Made dependency-health and circuit-breaker persistence fail open. A DNS/config failure in the observability store now logs a skipped health/circuit update but does not block the provider call.
- Added an explicit stateless provider policy path for MCP-internal provider calls. Extraction, discovery search execution, and ranking model calls now skip DB-backed dependency-health/circuit persistence inside private MCP services.

## Acceptance Criteria Coverage

- Downstream provider failures inside a reachable MCP service preserve provider/tool error code:
  - `tests/test_extraction_mcp_tools.py::test_extraction_mcp_client_preserves_structured_tool_error`
  - `tests/test_discovery_mcp_tools.py::test_coerce_mcp_list_result_preserves_structured_tool_error`
- MCP tool errors use a shared safe envelope:
  - `tests/test_mcp_runtime.py::test_run_mcp_tool_returns_structured_safe_tool_error`
- Dependency-health DNS/config failures do not block provider execution:
  - `tests/test_tool_policy.py::test_tool_policy_health_store_dns_failure_does_not_block_call`
- MCP stateless provider policy does not write dependency health:
  - `tests/test_tool_policy.py::test_tool_policy_can_skip_dependency_health_persistence`
- Existing MCP runtime allowlisting, provider policy, extraction, and discovery behavior remains covered by the existing focused suites.

## Verification

- `docker compose run --rm api python -m pytest tests/test_tool_policy.py tests/test_mcp_runtime.py tests/test_extraction_mcp_tools.py tests/test_discovery_mcp_tools.py`
  - 65 passed
- `python3 -m py_compile backend/app/mcp_runtime/tool_errors.py backend/app/mcp_servers/extraction/client.py backend/app/mcp_servers/extraction/server.py backend/app/mcp_servers/discovery/client.py backend/app/mcp_servers/discovery/server.py backend/app/mcp_servers/ranking/server.py backend/app/tool_policy.py backend/tests/test_mcp_runtime.py backend/tests/test_extraction_mcp_tools.py backend/tests/test_discovery_mcp_tools.py`
  - passed

## Remaining Manual Check

- After deploy, run one failing provider scenario and confirm Render logs identify the exact failing dependency/operation, for example `gemini` + `gemini_image_safety`, instead of only `extraction-mcp`.
