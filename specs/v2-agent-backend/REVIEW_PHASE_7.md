# V2 Agent Backend Review: Phase 7

## Spec Compliance

- Removed the transition-only `workflow_factory` hook from `AgentJobRunner`; the active Celery path now builds the final v2 graph directly.
- Added durable redacted attempt metadata to `job_attempts` for safe traceability without storing provider secrets, raw image bytes, or raw provider payloads.
- Added safe ranking-stage trace metadata: source product counts, candidate counts, and deterministic fallback markers.
- Updated Docker Compose with the `ranking-mcp` service and worker dependency.
- Updated `.env` and `.env.example` with matching `RANKING_MCP_URL` documentation.
- Updated README and `APPROACH.md` to reflect the final ranking MCP capability and traceability cleanup.
- Ran the required code-structure cleanup pass for the feature area.

## Acceptance Criteria Coverage

- Secrets and secret-bearing MCP URLs remain out of logs and persisted trace metadata.
- Frontend polling still receives the same public job statuses and brief shapes.
- The worker still uses `AgentJobRunner` as the only production execution path.
- Runtime environment documentation includes the new MCP service.

## Tests Run

- `python3 -m py_compile backend/app/ranking.py backend/app/mcp_servers/ranking/tools.py backend/app/mcp_servers/ranking/client.py backend/app/mcp_servers/ranking/server.py backend/app/agent/graph.py backend/app/agent/runner.py backend/app/job_repository.py backend/app/config.py`
- `docker compose run --rm --no-deps api python -m pytest tests/test_ranking_mcp_tools.py tests/test_v2_agent_runner.py -q`
- `docker compose run --rm --no-deps api python -m pytest tests/test_ranking_mcp_tools.py tests/test_discovery_mcp_tools.py tests/test_extraction_mcp_tools.py tests/test_v2_agent_runner.py tests/test_v2_agent_contracts.py tests/test_runtime_infrastructure_static.py tests/test_backend_gateway.py -q`
- `docker compose run --rm --no-deps api python -m pytest tests -q`

## Gaps

- Legacy `ResearchWorkflow` remains in the codebase for older provider-focused tests, but it is no longer the worker/runtime entrypoint.
- A live end-to-end REAL_MODE smoke should be run manually before deployment using reviewer-safe keys.

## Result

Approved for this phase.
