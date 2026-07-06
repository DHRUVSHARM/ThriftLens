# V2 Agent Backend Review: Phase 6

## Spec Compliance

- Implemented the Product Ranking MCP server with `score_candidates`, `detect_mismatches`, `group_candidates`, and `explain_match`.
- Moved scoring mechanics into `backend/app/ranking.py` so deterministic fallback and MCP ranking share one policy layer.
- Added score breakdowns for product type, brand/model, visual attributes, features, material/color/style, price fit, source confidence, availability, mismatch penalty, and final score.
- Added mismatch caveats for weak source evidence, missing required details, category uncertainty, material uncertainty, and brand uncertainty.
- Added user-facing grouping with closest first, cheaper products ascending by price, and premium products descending by price.
- Added optional Gemini ranking overlay behind `GEMINI_RANKING_ENABLED`; deterministic scoring remains the default and fallback.
- Wired LangGraph ranking nodes after product normalization and before final brief persistence.

## Acceptance Criteria Coverage

- Ranking uses score breakdowns and mismatch flags when available.
- Ranking server/model failure falls back to deterministic ranking.
- Final brief preserves source-backed ranked products and ranking explanations.
- Frontend-compatible `ProductResearchBrief` and `RankedProduct` shapes are preserved.

## Tests Run

- `python3 -m py_compile backend/app/ranking.py backend/app/mcp_servers/ranking/tools.py backend/app/mcp_servers/ranking/client.py backend/app/mcp_servers/ranking/server.py backend/app/agent/graph.py backend/app/agent/runner.py backend/app/job_repository.py backend/app/config.py`
- `docker compose run --rm --no-deps api python -m pytest tests/test_ranking_mcp_tools.py tests/test_v2_agent_runner.py -q`
- `docker compose run --rm --no-deps api python -m pytest tests/test_ranking_mcp_tools.py tests/test_discovery_mcp_tools.py tests/test_extraction_mcp_tools.py tests/test_v2_agent_runner.py tests/test_v2_agent_contracts.py tests/test_runtime_infrastructure_static.py tests/test_backend_gateway.py -q`
- `docker compose run --rm --no-deps api python -m pytest tests -q`

## Gaps

- Optional live Gemini ranking overlay is covered by mocked/default-off paths, not live quota-spending tests.
- Ranking explanations are intentionally concise and source-grounded; richer merchandising copy should stay a UI/product iteration, not ranking policy.

## Result

Approved for this phase.
