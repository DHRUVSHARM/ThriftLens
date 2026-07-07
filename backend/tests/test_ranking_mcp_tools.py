import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from app.config import Settings
import app.mcp_servers.ranking.tools as ranking_tools
from app.mcp_servers.ranking.tools import detect_mismatches_tool, explain_match_tool, group_candidates_tool, score_candidates_tool
from app.tool_policy import ToolExecutionPolicy


REFERENCE = {
    "productType": "blazer",
    "title": "navy wool blazer",
    "brand": None,
    "color": "navy",
    "materials": ["wool"],
    "keyFeatures": ["tailored"],
    "searchQueries": ["navy wool blazer"],
    "confidence": 0.84,
    "assumptions": [],
}

PROFILE = {
    "productFamily": "apparel",
    "refinedProductType": "blazer",
    "consumerDecisionFactors": ["material", "color", "fit", "price"],
    "importantProductDetails": ["navy wool blazer"],
    "recommendedEngines": ["google_shopping", "ebay"],
    "engineRationale": {"google_shopping": "Broad.", "ebay": "Used."},
    "rankingPriorities": ["same category", "same material", "same color"],
    "confidence": 0.8,
}

CONTEXT = {
    "exactTerms": ["navy wool blazer"],
    "broadTerms": ["blazer"],
    "featureTerms": ["tailored"],
    "materialTerms": ["wool"],
    "styleTerms": ["fit"],
    "mustHaveDetails": ["blazer", "navy", "wool"],
    "optionalDetails": ["tailored"],
}


@pytest.mark.anyio
async def test_ranking_tools_score_detect_group_and_explain() -> None:
    products = [
        {
            "source": "serpapi-google-shopping",
            "title": "Navy Wool Blazer",
            "retailer": "Example Tailor",
            "url": "https://example.com/navy-wool-blazer",
            "price": 120,
            "currency": "USD",
            "availability": "in stock",
            "freshness": "live",
        },
        {
            "source": "serpapi-google-shopping",
            "title": "Budget Blazer",
            "retailer": "Outlet",
            "url": "https://example.com/budget-blazer",
            "price": 45,
            "currency": "USD",
            "availability": "in stock",
            "freshness": "live",
        },
        {
            "source": "serpapi-google-shopping",
            "title": "Premium Navy Wool Blazer",
            "retailer": "Premium Store",
            "url": "https://example.com/premium-blazer",
            "price": 300,
            "currency": "USD",
            "availability": "limited",
            "freshness": "live",
        },
    ]

    scored = await score_candidates_tool(
        product_reference=REFERENCE,
        product_profile=PROFILE,
        search_context=CONTEXT,
        source_products=products,
        preferences={},
        settings=Settings(provider_mode="SAMPLE_MODE"),
    )
    assert scored[0]["scoreBreakdown"]["finalScore"] > 0
    assert "Matched:" in scored[0]["reason"]
    assert "navy" in scored[0]["reason"]

    mismatched = await detect_mismatches_tool(
        product_reference=REFERENCE,
        product_profile=PROFILE,
        search_context=CONTEXT,
        ranked_products=scored,
    )
    assert any(item["mismatches"] for item in mismatched)

    grouped = await group_candidates_tool(ranked_products=mismatched, preferences={})
    cheaper_prices = [item["product"]["price"] for item in grouped if item["group"] == "cheaper"]
    premium_prices = [item["product"]["price"] for item in grouped if item["group"] == "premium"]
    assert cheaper_prices == sorted(cheaper_prices)
    assert premium_prices == sorted(premium_prices, reverse=True)

    explanation = await explain_match_tool(
        product_reference=REFERENCE,
        product_profile=PROFILE,
        search_context=CONTEXT,
        ranked_products=grouped,
        settings=Settings(provider_mode="SAMPLE_MODE"),
    )
    assert explanation["summary"].startswith("Compared 3 source-backed candidates")
    assert "classified as apparel" in explanation["summary"]
    assert "checked required details" in explanation["summary"]
    assert "method" in explanation


@pytest.mark.anyio
async def test_ranking_tool_flags_weak_source_evidence() -> None:
    scored = await score_candidates_tool(
        product_reference=REFERENCE,
        product_profile=PROFILE,
        search_context=CONTEXT,
        source_products=[
            {
                "source": "serpapi-google-shopping",
                "title": "Navy Blazer",
                "retailer": None,
                "url": None,
                "price": None,
                "currency": "USD",
            }
        ],
        preferences={},
        settings=Settings(provider_mode="SAMPLE_MODE"),
    )
    mismatched = await detect_mismatches_tool(
        product_reference=REFERENCE,
        product_profile=PROFILE,
        search_context=CONTEXT,
        ranked_products=scored,
    )

    codes = [mismatch["code"] for mismatch in mismatched[0]["mismatches"]]
    assert "weak_source_evidence" in codes


def test_plain_model_summary_extracts_json_summary() -> None:
    assert (
        ranking_tools._plain_model_summary('{"summary":"The closest match keeps the product type and source-backed price."}')
        == "The closest match keeps the product type and source-backed price."
    )


@pytest.mark.anyio
async def test_ranking_tools_apply_gemini_overlay_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    async def fake_model_score_candidates(**kwargs):
        calls["score"] = kwargs
        return ranking_tools.RankingModelAssessment(
            candidates=[
                ranking_tools.RankingModelCandidateAssessment(
                    candidateIndex=0,
                    semanticScore=0.96,
                    reason="Strong semantic match: same navy wool blazer, material, color, and product type.",
                    mismatchCodes=[],
                ),
                ranking_tools.RankingModelCandidateAssessment(
                    candidateIndex=1,
                    semanticScore=0.22,
                    reason="Material conflict: the candidate is a cotton sport coat, not a wool blazer.",
                    mismatchCodes=["material_conflict"],
                ),
            ],
            summary="Gemini compared the candidates against the extracted blazer evidence.",
        )

    async def fake_model_explain_ranking(**kwargs):
        calls["explain"] = kwargs
        return "Gemini summary: strongest match keeps the product type, navy color, wool material, and source-backed price."

    monkeypatch.setattr(ranking_tools, "_model_score_candidates", fake_model_score_candidates)
    monkeypatch.setattr(ranking_tools, "_model_explain_ranking", fake_model_explain_ranking)

    settings = Settings(
        provider_mode="REAL_MODE",
        gemini_ranking_enabled=True,
        gemini_api_key="test-gemini-key",
        gemini_ranking_model="gemini-test-ranking-model",
    )
    scored = await score_candidates_tool(
        product_reference=REFERENCE,
        product_profile=PROFILE,
        search_context=CONTEXT,
        source_products=[
            {
                "source": "serpapi-google-shopping",
                "title": "Navy Wool Blazer",
                "retailer": "Example Tailor",
                "url": "https://example.com/navy-wool-blazer",
                "price": 120,
                "currency": "USD",
                "availability": "in stock",
                "freshness": "live",
            },
            {
                "source": "serpapi-google-shopping",
                "title": "Navy Cotton Sport Coat",
                "retailer": "Outlet",
                "url": "https://example.com/navy-cotton-sport-coat",
                "price": 95,
                "currency": "USD",
                "availability": "in stock",
                "freshness": "live",
            },
        ],
        preferences={},
        settings=settings,
    )

    assert "score" in calls
    assert scored[0]["reason"].startswith("Strong semantic match")
    assert scored[1]["mismatches"][0]["code"] == "material_conflict"
    assert "cotton sport coat" in scored[1]["mismatches"][0]["message"]

    explanation = await explain_match_tool(
        product_reference=REFERENCE,
        product_profile=PROFILE,
        search_context=CONTEXT,
        ranked_products=scored,
        settings=settings,
    )

    assert "explain" in calls
    assert explanation["modelSummary"].startswith("Gemini summary:")
    assert explanation["summary"].startswith("Compared 2 source-backed candidates")


@pytest.mark.anyio
async def test_ranking_model_calls_run_sync_sdk_in_worker_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_calls: list[dict[str, object]] = []
    to_thread_calls: list[str] = []

    async def fake_to_thread(func, /, *args, **kwargs):  # type: ignore[no-untyped-def]
        to_thread_calls.append(func.__name__)
        return func(*args, **kwargs)

    monkeypatch.setattr("app.mcp_servers.ranking.tools.asyncio.to_thread", fake_to_thread)

    class FakeGenerateContentConfig:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    class FakeModels:
        def generate_content(self, **kwargs: object) -> SimpleNamespace:
            captured_calls.append(kwargs)
            return SimpleNamespace(
                text=json.dumps(
                    {
                        "candidates": [
                            {
                                "candidateIndex": 0,
                                "semanticScore": 0.91,
                                "reason": "Same product type, color, and source-backed title.",
                                "mismatchCodes": [],
                            }
                        ],
                        "summary": "Model assessed one candidate.",
                    }
                )
            )

    class FakeClient:
        def __init__(self, *, api_key: str) -> None:
            self.api_key = api_key
            self.models = FakeModels()

    google_module = ModuleType("google")
    genai_module = ModuleType("google.genai")
    types_module = ModuleType("google.genai.types")
    genai_module.Client = FakeClient  # type: ignore[attr-defined]
    genai_module.types = types_module  # type: ignore[attr-defined]
    types_module.GenerateContentConfig = FakeGenerateContentConfig  # type: ignore[attr-defined]
    google_module.genai = genai_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_module)

    scored = await score_candidates_tool(
        product_reference=REFERENCE,
        product_profile=PROFILE,
        search_context=CONTEXT,
        source_products=[
            {
                "source": "serpapi-google-shopping",
                "title": "Navy Wool Blazer",
                "retailer": "Example Tailor",
                "url": "https://example.com/navy-wool-blazer",
                "price": 120,
                "currency": "USD",
            }
        ],
        preferences={},
        settings=Settings(provider_mode="SAMPLE_MODE"),
    )

    assessment = await ranking_tools._model_score_candidates(
        product_reference=ranking_tools.ProductReference.model_validate(REFERENCE),
        product_profile=ranking_tools.ProductDiscoveryProfile.model_validate(PROFILE),
        search_context=ranking_tools.ProductSearchContext.model_validate(CONTEXT),
        ranked_products=[ranking_tools.RankedProduct.model_validate(scored[0])],
        settings=Settings(provider_mode="REAL_MODE", gemini_api_key="test-key", gemini_ranking_model="test-ranking"),
        policy=ToolExecutionPolicy(timeout_seconds=1, max_retries=0, circuit_breaker_enabled=False),
    )

    assert assessment.candidates[0].semantic_score == 0.91
    assert to_thread_calls == ["generate_content"]
    assert captured_calls[0]["model"] == "test-ranking"
    assert "ProductReference" in str(captured_calls[0]["contents"])
