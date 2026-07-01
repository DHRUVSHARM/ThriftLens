# Provider Integrations Review

Status: Approved for next slice

## Spec Compliance

- Pass: Gemini provider code is isolated in `GeminiExtractionProvider` and validates extraction output against the `ProductReference` contract.
- Pass: Gemini extraction supports text and image inputs through the same provider boundary, with raw image bytes loaded from object storage metadata when needed.
- Pass: Malformed Gemini structured output gets one repair pass before a structured provider error is raised.
- Pass: SerpAPI hosted MCP configuration is isolated in `SerpApiMCPResearchProvider` and uses server-side path-auth URL construction.
- Pass: SerpAPI V1 calls are restricted to Google Shopping and allowlisted parameters.
- Pass: SerpAPI responses normalize into `SourceProduct` contracts with source-backed prices only; missing prices remain unknown.
- Pass: `ToolExecutionPolicy` owns timeout, bounded retry, dependency health updates, and safe provider error normalization.
- Pass: `REAL_MODE`, `SAMPLE_MODE`, and `TEST_MODE` are selected through the provider factory; non-real modes avoid live provider calls.
- Pass: Provider keys and secret-bearing MCP URLs are not returned to frontend-facing responses.

## Acceptance Criteria Coverage

- Gemini image extraction returns a schema-valid `ProductReference` or structured extraction error: covered by provider implementation and compile/static validation; live image smoke remains explicit opt-in.
- Gemini text extraction returns a schema-valid `ProductReference` or structured extraction error: covered by `test_gemini_text_extraction_returns_schema_valid_reference`.
- Prompt-injection attempts in text do not alter workflow transitions or tool selection: covered by `test_prompt_injection_text_does_not_change_workflow_stages`.
- SerpAPI MCP calls use only allowed engine/params in V1: covered by `test_serpapi_search_params_are_allowlisted` and `test_serpapi_mcp_client_invokes_langchain_search_tool_with_allowed_params`.
- SerpAPI results normalize into `SourceProduct` with source-backed prices only: covered by `test_serpapi_results_normalize_source_backed_prices_and_unknown_missing_price`.
- Missing price is represented as unknown, not estimated: covered by `test_serpapi_results_normalize_source_backed_prices_and_unknown_missing_price`.
- SerpAPI auth secrets are not logged and are not returned to frontend responses: covered by `test_serpapi_mcp_config_uses_server_side_secret_and_sanitized_summary`.
- Sample mode uses deterministic fixtures and labels results sample/static: covered by existing gateway and worker sample-mode tests.
- Test mode never calls Gemini or SerpAPI: covered by `test_test_mode_uses_fixture_workflow_without_live_providers`.
- Live provider smoke tests run only when explicitly enabled: covered by `test_live_provider_smoke_requires_explicit_flag`.
- Tool execution policy retries, timeout handling, dependency health updates, and safe error normalization: covered by `tests/test_tool_policy.py`.

## Identified Gaps

- No blocking provider integration gaps for mocked/tested behavior.
- Live Gemini and SerpAPI smoke checks are intentionally opt-in because they require paid/external keys and network access.
- The exact hosted MCP network behavior should be exercised once real SerpAPI credentials are available.
- Generated reference images remain out of scope for V1.

## Improvement Suggestions

- Add an explicit live-smoke command once real provider keys are configured.
- Add duration metrics to provider attempts when observability is expanded.
- Consider persisting sanitized provider connection summaries for diagnostics if frontend support needs it later.

## Verification Commands

- `python3 -m py_compile backend/app/config.py backend/app/gemini_provider.py backend/app/provider_factory.py backend/app/serpapi_provider.py backend/app/tool_policy.py backend/app/workflow.py backend/app/object_storage.py`
- `docker compose build api worker`
- `docker compose up -d --force-recreate api worker`
- `docker compose exec api python -m pytest tests/test_provider_integrations.py`
- `docker compose exec api python -m pytest tests/test_tool_policy.py`
- `docker compose exec api python -m pytest tests`
