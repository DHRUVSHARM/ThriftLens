# V2 Agent Backend Review: Phase 5

## Spec Compliance

- Implemented the Product Discovery MCP server as the combined context/research boundary.
- Added discovery contracts for product profile, search context, search plan, raw execution result, and source errors.
- Added graph-driven discovery nodes after reference persistence and before ranking.
- Kept model use limited to structured product profile and search-plan generation in REAL_MODE.
- Kept actual SerpAPI execution code-driven through a validated search plan and shared MCP runtime.
- Preserved `SourceProduct` and `ProductResearchBrief` as app-facing contracts.

## Acceptance Criteria Coverage

- Product discovery produces `ProductDiscoveryProfile`.
- Search planning validates engine allowlist, allowed params, max engines, and call budget.
- SerpAPI calls are behind the Product Discovery MCP server and shared MCP runtime.
- Provider/source failure after product reference produces a partial result.
- Source products normalize to `SourceProduct[]`.
- Frontend-compatible final/partial brief shapes are preserved.

## Tests Run

- `python3 -m py_compile backend/app/workflow_contracts.py backend/app/mcp_servers/discovery/tools.py backend/app/mcp_servers/discovery/client.py backend/app/mcp_servers/discovery/server.py backend/app/agent/graph.py backend/app/agent/runner.py`
- `docker compose config --quiet`
- `docker compose build api worker extraction-mcp discovery-mcp`
- `docker compose run --rm --no-deps api python -m pytest tests/test_discovery_mcp_tools.py tests/test_v2_agent_runner.py tests/test_v2_agent_contracts.py tests/test_worker_orchestration.py tests/test_backend_gateway.py`
- `docker compose run --rm --no-deps api python -m pytest tests/test_provider_integrations.py tests/test_extraction_mcp_tools.py`

## Gaps

- Ranking is still deterministic and is intentionally deferred to Phase 6.
- SerpAPI engine schema discovery is represented as a static allowlist in this phase; optional runtime schema refresh can be added later if needed.
- Old `ResearchWorkflow` remains for compatibility tests and will be removed or retired during Phase 7 cleanup after ranking migration.

## Result

Approved for this phase.
