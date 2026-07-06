# Review: Text Safety And Refinement Hardening

## Spec Compliance

- Added `TextSafetyResult` and `extraction.screen_text_safety` to the v2 extraction boundary.
- Updated the LangGraph routing so text-only jobs and image jobs with optional focus text screen text before extraction or source research.
- Preserved image-first safety behavior for image-only jobs.
- Improved multi-product refinement copy so it describes multiple products/objects instead of implying the image is not a product.
- Simplified best-available match UI copy so the no-exact-match caveat is not repeated above the card and in trust/evidence.
- Added a regulated-product guardrail for firearms, ammunition, suppressors, and explosive categories so these stop before source research and cannot return shopping links.
- Added a post-extraction regulated-product check so image-derived product references cannot bypass text screening.
- Centralized unsafe category definitions, safety messages, known product hint terms, and image unsafe reason allowlist in `backend/app/product_safety.py`.
- Added an optional Gemini text-safety classifier for long-tail unsafe/regulated cases that deterministic rules do not enumerate.
- Kept deterministic central-policy screening as the fast path and fallback so obvious prompt-injection, malformed, link-request, unsafe-media, and regulated-product cases do not need a model call.
- Added configured thresholds so low-confidence model-safe results become refinement instead of source research.
- Tightened deterministic product intent so general knowledge/list requests such as "top 10 countries" stop as non-product requests.
- Added a post-extraction product-reference gate so schema-valid but non-product references stop before discovery/source search.
- Filtered generic Google organic results that have no product evidence before rendering source-backed product cards.
- Extended discovery normalization so shopping and non-shopping source results require product-shaped evidence before becoming product cards.
- Normalized model-generated ranking summaries into plain prose so trust/evidence does not render raw JSON.
- Reduced product-card reasoning to one concise signal or caveat by default, with fuller detail only as an accessibility/native title hint.

## Acceptance Criteria Coverage

- Text prompt injection stops before extraction/search: covered by `test_agent_job_runner_prompt_injected_text_requests_refinement_before_extraction`.
- Unsafe text stops before extraction/search: covered by `test_agent_job_runner_unsafe_text_fails_before_extraction`.
- Malformed text requests refinement: covered by `test_screen_text_safety_requests_refinement_for_malformed_text`.
- Link-style assistant requests do not become product search queries: covered by `test_screen_text_safety_blocks_link_request_even_with_product_terms`.
- Regulated text product requests stop before extraction/search: covered by `test_screen_text_safety_blocks_regulated_weapon_products` and `test_agent_job_runner_regulated_product_text_fails_with_specific_code`.
- Regulated image-derived references stop before discovery/search: covered by `test_agent_job_runner_regulated_image_reference_fails_before_discovery`.
- Image safety keeps central disallowed categories such as firearms unsafe: covered by `test_screen_image_safety_treats_firearms_reason_as_disallowed`.
- Model text-safety overlay can block long-tail regulated categories: covered by `test_screen_text_safety_uses_model_classifier_for_long_tail_when_enabled`.
- Model text-safety overlay can allow long-tail product descriptions that do not match the known product hint list: covered by `test_screen_text_safety_defers_unknown_product_hint_to_model`.
- Low-confidence model-safe output asks for refinement: covered by `test_screen_text_safety_treats_low_confidence_model_safe_as_unclear`.
- Deterministic high-risk blocks skip the model call: covered by `test_screen_text_safety_deterministic_block_skips_model`.
- General knowledge/list requests stop before extraction/search: covered by `test_screen_text_safety_blocks_non_product_knowledge_request`.
- Schema-valid non-product references stop before discovery/search: covered by `test_agent_job_runner_non_product_reference_requests_refinement_before_discovery`.
- Generic organic search links without product evidence are filtered before product-card rendering: covered by `test_normalize_discovery_response_filters_generic_google_links_without_product_evidence`.
- Shopping and non-Google generic links without product evidence are filtered before product-card rendering: covered by `test_normalize_discovery_response_filters_shopping_links_without_product_evidence` and `test_normalize_discovery_response_filters_non_google_generic_links`.
- JSON-shaped ranking model summaries are rendered as plain prose: covered by `test_plain_model_summary_extracts_json_summary`.
- Ambiguous multi-product image uses clearer refinement copy: covered by `test_agent_job_runner_ambiguous_image_requests_refinement` and worker orchestration coverage.

## Gaps

- Known product hint terms are a cheap deterministic signal and sample-mode fallback, not the source of truth in real mode. Unknown product descriptions defer to the thresholded text-safety model when it is enabled.
- If `TEXT_SAFETY_MODEL_ENABLED=false` or the model is unavailable, the known product-term list remains a conservative fallback and valid niche products may still ask for refinement.
- Regulated-product blocking is intentionally conservative. The current scope is common firearms/ammunition/explosive terms, not a complete policy taxonomy.
- The generic-link filter only applies to web-search results without product evidence; real product results with price, image, or product URL continue through normalization.

## Verification

- `python3 -m py_compile backend/app/product_safety.py backend/app/mcp_servers/extraction/tools.py backend/app/agent/graph.py backend/app/mcp_servers/discovery/tools.py backend/app/mcp_servers/ranking/tools.py backend/tests/test_extraction_mcp_tools.py backend/tests/test_v2_agent_runner.py backend/tests/test_discovery_mcp_tools.py backend/tests/test_ranking_mcp_tools.py`
- `python3 -m py_compile backend/app/product_safety.py backend/app/mcp_servers/extraction/tools.py backend/app/mcp_servers/discovery/tools.py backend/tests/test_extraction_mcp_tools.py backend/tests/test_discovery_mcp_tools.py`
- `python3 -m py_compile backend/app/product_safety.py backend/app/config.py backend/app/gemini_provider.py backend/app/sample_providers.py backend/app/mcp_servers/extraction/tools.py backend/tests/test_extraction_mcp_tools.py`
- `docker compose exec -T api sh -lc 'PYTHONPATH=/app pytest tests/test_extraction_mcp_tools.py tests/test_v2_agent_runner.py tests/test_discovery_mcp_tools.py tests/test_ranking_mcp_tools.py -q'`
- `docker compose exec -T api sh -lc 'PYTHONPATH=/app pytest tests/test_extraction_mcp_tools.py tests/test_discovery_mcp_tools.py tests/test_v2_agent_runner.py -q'`
- `docker compose exec -T api sh -lc 'TEXT_SAFETY_MODEL_ENABLED=false PYTHONPATH=/app pytest tests/test_extraction_mcp_tools.py tests/test_v2_agent_runner.py tests/test_discovery_mcp_tools.py -q'`
- `docker compose exec -T api sh -lc 'TEXT_SAFETY_MODEL_ENABLED=false PYTHONPATH=/app pytest tests/test_extraction_mcp_tools.py tests/test_v2_agent_runner.py -q'`
- Direct gate check: `give me the top 10 countries in the world` returns `non_product_request` with `knowledge_or_list_request`.
- `docker compose run --build --rm frontend npm run build`
- `git diff --check`
- Restarted/recreated affected services after env/code changes: `api`, `worker`, `extraction-mcp`, `discovery-mcp`, `ranking-mcp`, and rebuilt/recreated `frontend` where UI changed.
- API health verified from inside the API container.
