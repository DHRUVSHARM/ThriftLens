import pytest
import types

from app.config import Settings
from app.mcp_runtime.tool_errors import mcp_tool_error_payload
from app.mcp_servers.discovery.client import DiscoveryMCPToolClient, coerce_mcp_list_result, search_plan_timeout_seconds
from app.mcp_servers.discovery.tools import (
    _call_gemini_json,
    build_search_context_tool,
    classify_product_profile_tool,
    normalize_discovery_response,
    normalize_products_tool,
    plan_search_sources_tool,
    validate_search_plan,
)
from app.workflow_contracts import (
    ProductDiscoveryProfile,
    ProductReference,
    ProductSearchContext,
    ProductSearchPlan,
    ProductSearchPlanItem,
    WorkflowProviderError,
)


def test_validate_search_plan_filters_engines_params_and_budget() -> None:
    settings = Settings(
        provider_mode="SAMPLE_MODE",
        serpapi_max_calls_per_job=2,
        discovery_max_engines=2,
        discovery_engine_allowlist="google_shopping,ebay",
    )
    reference = ProductReference(
        productType="blazer",
        title="navy wool blazer",
        color="navy",
        materials=["wool"],
        keyFeatures=["tailored"],
        searchQueries=["navy wool blazer"],
        confidence=0.8,
        assumptions=[],
    )
    profile = ProductDiscoveryProfile(
        productFamily="apparel",
        refinedProductType="blazer",
        recommendedEngines=["google_shopping", "ebay"],
        engineRationale={"google_shopping": "Broad.", "ebay": "Used."},
    )
    context = ProductSearchContext(exactTerms=["navy wool blazer"], mustHaveDetails=["blazer", "wool"])
    plan = ProductSearchPlan(
        planItems=[
            ProductSearchPlanItem(
                engine="google_shopping",
                params={"engine": "google_shopping", "q": "navy wool blazer", "api_key": "secret", "num": 99},
                priority=1,
            ),
            ProductSearchPlanItem(
                engine="home_depot",
                params={"engine": "home_depot", "q": "navy wool blazer"},
                priority=2,
            ),
            ProductSearchPlanItem(
                engine="ebay",
                params={"engine": "ebay", "_nkw": "navy wool blazer"},
                priority=3,
            ),
        ]
    )

    validated = validate_search_plan(plan, reference, profile, context, {}, settings)

    assert [item.engine for item in validated.plan_items] == ["google_shopping", "ebay"]
    assert "api_key" not in validated.plan_items[0].params
    assert validated.plan_items[0].params["num"] == 10


def test_validate_search_plan_allows_distinct_shopping_queries_for_alternatives() -> None:
    settings = Settings(
        provider_mode="SAMPLE_MODE",
        serpapi_max_calls_per_job=2,
        discovery_max_engines=2,
        discovery_engine_allowlist="google_shopping,google",
    )
    reference = ProductReference(
        productType="t-shirt",
        title="red crew neck t-shirt",
        color="red",
        keyFeatures=["crew neck", "short sleeve", "solid color"],
        searchQueries=["red crew neck t-shirt"],
        confidence=0.9,
        assumptions=[],
    )
    profile = ProductDiscoveryProfile(
        productFamily="apparel",
        refinedProductType="t-shirt",
        recommendedEngines=["google_shopping", "google"],
    )
    context = ProductSearchContext(
        exactTerms=["red crew neck t-shirt"],
        featureTerms=["crew neck", "short sleeve", "solid color"],
        styleTerms=["casual"],
        mustHaveDetails=["t-shirt", "red"],
    )
    plan = ProductSearchPlan(
        planItems=[
            ProductSearchPlanItem(
                engine="google_shopping",
                params={"engine": "google_shopping", "q": "red crew neck t-shirt", "num": 10},
                intent="closest_match",
                priority=1,
            ),
            ProductSearchPlanItem(
                engine="google",
                params={"engine": "google", "q": "red crew neck t-shirt", "num": 10},
                intent="closest_match",
                priority=2,
            ),
        ]
    )

    validated = validate_search_plan(plan, reference, profile, context, {}, settings)

    assert [item.engine for item in validated.plan_items] == ["google_shopping", "google_shopping"]
    assert [item.intent for item in validated.plan_items] == ["closest_match", "similar_alternatives"]
    assert validated.plan_items[0].params["q"] != validated.plan_items[1].params["q"]
    assert "short sleeve" in validated.plan_items[1].params["q"]


def test_validate_search_plan_appends_similar_search_when_budget_allows() -> None:
    settings = Settings(
        provider_mode="SAMPLE_MODE",
        serpapi_max_calls_per_job=2,
        discovery_max_engines=2,
        discovery_engine_allowlist="google_shopping",
    )
    reference = ProductReference(productType="table lamp", title="green ceramic table lamp", color="green", keyFeatures=["ceramic"], searchQueries=["green ceramic table lamp"])
    profile = ProductDiscoveryProfile(productFamily="home_goods", refinedProductType="table lamp", recommendedEngines=["google_shopping"])
    context = ProductSearchContext(featureTerms=["ceramic"], mustHaveDetails=["table lamp", "green"])
    plan = ProductSearchPlan(
        planItems=[
            ProductSearchPlanItem(
                engine="google_shopping",
                params={"engine": "google_shopping", "q": "green ceramic table lamp"},
                intent="closest_match",
                priority=1,
            )
        ]
    )

    validated = validate_search_plan(plan, reference, profile, context, {}, settings)

    assert len(validated.plan_items) == 2
    assert validated.plan_items[1].intent == "similar_alternatives"


def test_validate_search_plan_keeps_family_specific_second_engine_when_budget_is_full() -> None:
    settings = Settings(
        provider_mode="SAMPLE_MODE",
        serpapi_max_calls_per_job=2,
        discovery_max_engines=2,
        discovery_engine_allowlist="google_shopping,ebay",
    )
    reference = ProductReference(
        productType="blazer",
        title="navy wool blazer",
        color="navy",
        materials=["wool"],
        keyFeatures=["tailored"],
        searchQueries=["navy wool blazer"],
    )
    profile = ProductDiscoveryProfile(
        productFamily="apparel",
        refinedProductType="blazer",
        recommendedEngines=["google_shopping", "ebay"],
    )
    context = ProductSearchContext(materialTerms=["wool"], mustHaveDetails=["blazer", "navy", "wool"])
    plan = ProductSearchPlan(
        planItems=[
            ProductSearchPlanItem(
                engine="google_shopping",
                params={"engine": "google_shopping", "q": "navy wool blazer"},
                intent="closest_match",
                priority=1,
            ),
            ProductSearchPlanItem(
                engine="ebay",
                params={"engine": "ebay", "_nkw": "navy wool blazer"},
                intent="similar_alternatives",
                priority=2,
            ),
        ]
    )

    validated = validate_search_plan(plan, reference, profile, context, {}, settings)

    assert [item.engine for item in validated.plan_items] == ["google_shopping", "ebay"]
    assert [item.intent for item in validated.plan_items] == ["closest_match", "similar_alternatives"]


def test_validate_search_plan_diversifies_duplicate_shopping_alternative_when_profile_recommends_source() -> None:
    settings = Settings(
        provider_mode="SAMPLE_MODE",
        serpapi_max_calls_per_job=2,
        discovery_max_engines=2,
        discovery_engine_allowlist="google_shopping,ebay,amazon",
    )
    reference = ProductReference(
        productType="t-shirt",
        title="red crew neck t-shirt",
        color="red",
        keyFeatures=["crew neck", "short sleeves"],
        searchQueries=["red crew neck t-shirt"],
    )
    profile = ProductDiscoveryProfile(
        productFamily="apparel",
        refinedProductType="t-shirt",
        recommendedEngines=["google_shopping", "ebay", "amazon"],
        engineRationale={"ebay": "Useful for apparel alternatives and resale pricing."},
    )
    context = ProductSearchContext(featureTerms=["crew neck", "short sleeves"], mustHaveDetails=["t-shirt", "red"])
    plan = ProductSearchPlan(
        planItems=[
            ProductSearchPlanItem(
                engine="google_shopping",
                params={"engine": "google_shopping", "q": "red crew neck t-shirt"},
                intent="closest_match",
                priority=1,
            ),
            ProductSearchPlanItem(
                engine="google_shopping",
                params={"engine": "google_shopping", "q": "red t-shirt alternatives"},
                intent="similar_alternatives",
                priority=2,
            ),
        ]
    )

    validated = validate_search_plan(plan, reference, profile, context, {}, settings)

    assert [item.engine for item in validated.plan_items] == ["google_shopping", "ebay"]
    assert validated.plan_items[1].intent == "similar_alternatives"
    assert validated.plan_items[1].params["_nkw"]


def test_coerce_mcp_list_result_handles_text_wrapped_lists() -> None:
    assert coerce_mcp_list_result({"type": "text", "text": '[{"title": "navy blazer"}]'}) == [{"title": "navy blazer"}]
    assert coerce_mcp_list_result({"structuredContent": [{"title": "navy blazer"}]}) == [{"title": "navy blazer"}]


def test_coerce_mcp_list_result_preserves_structured_tool_error() -> None:
    result = mcp_tool_error_payload(
        WorkflowProviderError("provider_rate_limited", "Provider is temporarily rate-limited.", retryable=True),
        dependency="serpapi",
        operation="discovery_search_sources",
        origin_code="provider_rate_limited",
    )

    with pytest.raises(WorkflowProviderError) as exc_info:
        coerce_mcp_list_result(result)

    assert exc_info.value.code == "provider_rate_limited"
    assert getattr(exc_info.value, "dependency") == "serpapi"
    assert getattr(exc_info.value, "operation") == "discovery_search_sources"


def test_search_plan_timeout_scales_with_planned_calls_and_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.mcp_servers.discovery.client.get_settings",
        lambda: Settings(
            provider_timeout_seconds=20,
            provider_max_retries=1,
            provider_backoff_base_seconds=2,
            serpapi_max_calls_per_job=2,
        ),
    )
    plan = ProductSearchPlan(
        planItems=[
            ProductSearchPlanItem(
                engine="google_shopping",
                params={"engine": "google_shopping", "q": "red t-shirt"},
                priority=1,
            ),
            ProductSearchPlanItem(
                engine="ebay",
                params={"engine": "ebay", "_nkw": "red t-shirt"},
                priority=2,
            ),
        ]
    )

    assert search_plan_timeout_seconds(plan) == 89


@pytest.mark.anyio
async def test_discovery_client_uses_scaled_timeout_for_execute_search_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.mcp_servers.discovery.client.get_settings",
        lambda: Settings(
            provider_timeout_seconds=20,
            provider_max_retries=1,
            provider_backoff_base_seconds=2,
            serpapi_max_calls_per_job=2,
        ),
    )

    class FakeRuntime:
        def __init__(self) -> None:
            self.policy_timeout: float | None = None

        async def invoke_tool(self, **kwargs):  # type: ignore[no-untyped-def]
            self.policy_timeout = kwargs["policy"].timeout_seconds
            return {"rawResults": [], "sourceErrors": []}

    runtime = FakeRuntime()
    plan = ProductSearchPlan(
        planItems=[
            ProductSearchPlanItem(engine="google_shopping", params={"engine": "google_shopping", "q": "red t-shirt"}, priority=1),
            ProductSearchPlanItem(engine="ebay", params={"engine": "ebay", "_nkw": "red t-shirt"}, priority=2),
        ]
    )

    result = await DiscoveryMCPToolClient(runtime=runtime).execute_search_plan(search_plan=plan)  # type: ignore[arg-type]

    assert result.raw_results == []
    assert runtime.policy_timeout == 89


def test_coerce_mcp_list_result_aggregates_multiple_text_blocks() -> None:
    assert coerce_mcp_list_result(
        [
            {"type": "text", "text": '[{"title": "navy blazer"}]'},
            {"type": "text", "text": '[{"title": "gray blazer"}]'},
        ]
    ) == [{"title": "navy blazer"}, {"title": "gray blazer"}]


def test_normalize_discovery_response_filters_generic_google_links_without_product_evidence() -> None:
    products = normalize_discovery_response(
        "google",
        {
            "organic_results": [
                {
                    "title": "Guide to navy blazer style",
                    "source": "Example Blog",
                    "link": "https://example.com/blazer-guide",
                },
                {
                    "title": "Navy Wool Blazer",
                    "source": "Example Store",
                    "link": "https://example.com/navy-blazer",
                    "thumbnail": "https://example.com/navy-blazer.jpg",
                },
            ]
        },
    )

    assert [product["title"] for product in products] == ["Navy Wool Blazer"]


def test_normalize_discovery_response_filters_shopping_links_without_product_evidence() -> None:
    products = normalize_discovery_response(
        "google_shopping",
        {
            "shopping_results": [
                {
                    "title": "Firearm retailer education page",
                    "source": "Example Link",
                    "link": "https://example.com/generic-page",
                },
                {
                    "title": "Navy Wool Blazer",
                    "source": "Example Store",
                    "link": "https://example.com/navy-blazer",
                    "thumbnail": "https://example.com/navy-blazer.jpg",
                },
            ]
        },
    )

    assert [product["title"] for product in products] == ["Navy Wool Blazer"]


def test_normalize_discovery_response_filters_non_google_generic_links() -> None:
    products = normalize_discovery_response(
        "ebay",
        {
            "organic_results": [
                {
                    "title": "Article about navy blazer outfits",
                    "source": "Example Blog",
                    "link": "https://example.com/article",
                },
                {
                    "title": "Navy Wool Blazer",
                    "source": "Example Seller",
                    "link": "https://example.com/navy-blazer",
                    "price": "$49.00",
                },
            ]
        },
    )

    assert [product["title"] for product in products] == ["Navy Wool Blazer"]


@pytest.mark.anyio
async def test_discovery_tools_build_profile_context_plan_and_products() -> None:
    settings = Settings(provider_mode="SAMPLE_MODE", discovery_max_engines=2, serpapi_max_calls_per_job=2)
    reference = {
        "productType": "blazer",
        "title": "navy wool blazer",
        "brand": None,
        "color": "navy",
        "materials": ["wool"],
        "keyFeatures": ["tailored"],
        "searchQueries": ["navy wool blazer"],
        "confidence": 0.82,
        "assumptions": [],
    }

    profile = await classify_product_profile_tool(product_reference=reference, preferences={}, settings=settings)
    context = await build_search_context_tool(product_reference=reference, product_profile=profile)
    plan = await plan_search_sources_tool(
        product_reference=reference,
        product_profile=profile,
        search_context=context,
        preferences={},
        settings=settings,
    )

    assert profile["productFamily"] == "apparel"
    assert len(plan["planItems"]) <= 2
    assert plan["planItems"][0]["engine"] == "google_shopping"

    products = await normalize_products_tool(
        search_results={
            "rawResults": [
                {
                    "engine": "google_shopping",
                    "intent": "closest_match",
                    "params": {"engine": "google_shopping", "q": "navy wool blazer"},
                    "response": {
                        "shopping_results": [
                            {
                                "title": "navy wool blazer",
                                "source": "Example",
                                "link": "https://example.com",
                                "extracted_price": 49.99,
                            }
                        ]
                    },
                }
            ],
            "sourceErrors": [],
        }
    )

    assert products[0]["title"] == "navy wool blazer"
    assert products[0]["source"] == "serpapi-google-shopping"


@pytest.mark.anyio
async def test_discovery_model_call_uses_json_mode_without_gemini_response_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_config: dict[str, object] = {}
    captured_contents: list[str] = []

    class FakeGenerateContentConfig:
        def __init__(self, **kwargs: object) -> None:
            captured_config.update(kwargs)

    class FakeModels:
        def generate_content(self, *, model: str, contents: str, config: object) -> object:
            captured_contents.append(contents)
            return types.SimpleNamespace(
                text="""{
                    "productFamily": "apparel",
                    "refinedProductType": "t-shirt",
                    "shoppingIntent": "find_exact_or_similar",
                    "consumerDecisionFactors": ["category", "color", "fit", "price"],
                    "importantProductDetails": ["red", "crew neckline"],
                    "recommendedEngines": ["google_shopping"],
                    "engineRationale": {"google_shopping": "Broad current retailer coverage."},
                    "rankingPriorities": ["same product type", "same color"],
                    "queryParamHints": [],
                    "confidence": 0.8,
                    "uncertaintyNotes": []
                }"""
            )

    class FakeClient:
        def __init__(self, *, api_key: str) -> None:
            self.models = FakeModels()

    fake_types = types.SimpleNamespace(GenerateContentConfig=FakeGenerateContentConfig)
    fake_genai = types.SimpleNamespace(Client=FakeClient, types=fake_types)
    monkeypatch.setitem(__import__("sys").modules, "google", types.SimpleNamespace(genai=fake_genai))
    monkeypatch.setitem(__import__("sys").modules, "google.genai", fake_genai)
    monkeypatch.setitem(__import__("sys").modules, "google.genai.types", fake_types)

    raw = await _call_gemini_json(
        prompt="Classify a red t-shirt.",
        response_schema=ProductDiscoveryProfile,
        settings=Settings(provider_mode="REAL_MODE", gemini_api_key="test-key", gemini_extraction_model="gemini-test"),
    )

    assert raw["engineRationale"]["google_shopping"]
    assert captured_config == {"response_mime_type": "application/json"}
    assert "response_schema" not in captured_config
    assert "Required JSON shape" in captured_contents[0]
