import pytest
from pydantic import ValidationError

from app.agent.state import ProductResearchAgentState, safe_error_from_provider_error
from app.workflow_contracts import (
    CandidateMismatch,
    DiscoveryEngineRecommendation,
    ImageSafetyResult,
    ProductContext,
    ProductDiscoveryProfile,
    ProductSearchContext,
    ProductSearchExecutionResult,
    ProductSearchPlan,
    ProductSearchPlanItem,
    ProductSearchRawResult,
    ProductUnderstandingDecision,
    RankingScoreBreakdown,
    RankedProduct,
    ResearchQueryPlan,
    ResearchQueryPlanItem,
    SourceProduct,
    WorkflowProviderError,
)


def test_image_safety_result_uses_aliases_and_confidence_bounds() -> None:
    result = ImageSafetyResult(
        safetyStatus="unsafe",
        unsafeReasons=["nsfw"],
        confidence=0.91,
        userSafeMessage="Upload a product-focused image.",
    )

    assert result.safety_status == "unsafe"
    assert result.model_dump(by_alias=True)["unsafeReasons"] == ["nsfw"]

    with pytest.raises(ValidationError):
        ImageSafetyResult(safetyStatus="safe", confidence=1.2)


def test_product_context_captures_sourced_search_enrichment() -> None:
    context = ProductContext(
        canonicalName="unstructured wool blazer",
        categoryTerms=["men's blazer", "sport coat"],
        aliases=["unconstructed blazer"],
        exclusionTerms=["suit jacket"],
        sourceCitations=[
            {
                "title": "Blazer",
                "url": "https://example.test/blazer",
                "source": "public-context",
            }
        ],
        confidence="high",
    )

    dumped = context.model_dump(by_alias=True)
    assert dumped["canonicalName"] == "unstructured wool blazer"
    assert dumped["categoryTerms"] == ["men's blazer", "sport coat"]
    assert dumped["exclusionTerms"] == ["suit jacket"]
    assert dumped["sourceCitations"][0]["source"] == "public-context"


def test_product_understanding_decision_captures_bounded_tool_result() -> None:
    decision = ProductUnderstandingDecision(
        decision="extracted",
        productReference={
            "productType": "blazer",
            "title": "navy wool blazer",
            "materials": ["wool"],
            "keyFeatures": ["tailored"],
            "searchQueries": ["navy wool blazer"],
            "confidence": 0.84,
            "assumptions": [],
        },
        imageGateResult={
            "safetyStatus": "safe",
            "productSuitability": "multiple_products",
            "productLikenessConfidence": 0.9,
            "detectedProducts": [{"label": "navy wool blazer", "confidence": 0.92}],
            "needsClarification": True,
            "decision": "proceed",
            "reason": "Target product selected.",
        },
        requestPayload={"targetDescription": "the navy blazer"},
        toolCalls=["image_product_gate", "disambiguate_target_product", "extract_product_reference"],
        reason="Product gate passed and product reference was extracted.",
    )

    dumped = decision.model_dump(by_alias=True)
    assert dumped["productReference"]["productType"] == "blazer"
    assert dumped["imageGateResult"]["productSuitability"] == "multiple_products"
    assert dumped["toolCalls"][-1] == "extract_product_reference"


def test_research_query_plan_bounds_query_items() -> None:
    plan = ResearchQueryPlan(
        queries=[
            ResearchQueryPlanItem(
                query="navy unstructured wool blazer patch pockets",
                purpose="exact_match",
                maxResults=8,
            )
        ],
        searchTerms=["navy", "unstructured", "wool blazer"],
        exclusionTerms=["suit set"],
    )

    assert plan.queries[0].max_results == 8
    assert plan.model_dump(by_alias=True)["queries"][0]["maxResults"] == 8

    with pytest.raises(ValidationError):
        ResearchQueryPlanItem(query="", maxResults=30)


def test_product_discovery_contracts_capture_profile_plan_and_results() -> None:
    profile = ProductDiscoveryProfile(
        productFamily="apparel",
        refinedProductType="unstructured wool blazer",
        shoppingIntent="find_exact_or_similar",
        consumerDecisionFactors=["material", "fit", "color"],
        importantProductDetails=["navy color", "wool material"],
        recommendedEngines=["google_shopping", "ebay"],
        engineRationale={"google_shopping": "Broad coverage."},
        rankingPriorities=["same material", "same color"],
        confidence=0.82,
    )
    context = ProductSearchContext(
        exactTerms=["navy wool blazer"],
        materialTerms=["wool"],
        mustHaveDetails=["blazer", "navy"],
    )
    plan = ProductSearchPlan(
        planItems=[
            ProductSearchPlanItem(
                engine="google_shopping",
                params={"engine": "google_shopping", "q": "navy wool blazer"},
                intent="closest_match",
                priority=1,
            )
        ],
        selectedEngines=[DiscoveryEngineRecommendation(engine="google_shopping", priority=1, reason="Broad coverage.")],
        fallbackUsed=False,
    )
    results = ProductSearchExecutionResult(
        rawResults=[
            ProductSearchRawResult(
                engine="google_shopping",
                intent="closest_match",
                params={"engine": "google_shopping", "q": "navy wool blazer"},
                response={"shopping_results": []},
            )
        ]
    )

    assert profile.product_family == "apparel"
    assert context.model_dump(by_alias=True)["mustHaveDetails"] == ["blazer", "navy"]
    assert plan.model_dump(by_alias=True)["planItems"][0]["engine"] == "google_shopping"
    assert results.model_dump(by_alias=True)["rawResults"][0]["engine"] == "google_shopping"

    with pytest.raises(ValidationError):
        ProductDiscoveryProfile(productFamily="unknown", refinedProductType="x")


def test_ranked_product_accepts_score_breakdowns_and_mismatches() -> None:
    product = SourceProduct(
        source="serpapi-google-shopping",
        title="Navy Unstructured Wool Blazer",
        retailer="Example Retailer",
        price=185.0,
    )
    breakdown = RankingScoreBreakdown(
        productTypeMatch=0.9,
        visualAttributeMatch=0.8,
        sourceConfidence=0.7,
        mismatchPenalty=0.1,
        finalScore=0.82,
    )
    mismatch = CandidateMismatch(
        code="weak_source_evidence",
        severity="low",
        message="Source did not include material details.",
        evidence=["title match only"],
    )

    ranked = RankedProduct(
        product=product,
        score=0.82,
        group="closest",
        confidence="high",
        reason="Strong category and style match.",
        scoreBreakdown=breakdown,
        mismatches=[mismatch],
    )

    dumped = ranked.model_dump(by_alias=True)
    assert dumped["scoreBreakdown"]["finalScore"] == 0.82
    assert dumped["mismatches"][0]["code"] == "weak_source_evidence"

    with pytest.raises(ValidationError):
        RankingScoreBreakdown(finalScore=1.4)


def test_product_research_agent_state_defaults_to_safe_empty_sections() -> None:
    state = ProductResearchAgentState(
        identity={"jobId": "job-123", "providerMode": "TEST_MODE"},
        request={
            "inputType": "text",
            "requestPayload": {"textDescription": "navy wool blazer"},
            "preferences": {"rankingPreference": "grouped"},
        },
    )

    assert state.control.public_status == "queued"
    assert state.control.current_node == "start"
    assert state.research.source_products == []
    assert state.trace.redacted_tool_calls == []
    assert state.model_dump(by_alias=True)["identity"]["jobId"] == "job-123"


def test_safe_error_from_provider_error_keeps_user_safe_shape() -> None:
    error = WorkflowProviderError(
        "provider_rate_limited",
        "Provider is temporarily rate-limited.",
        retryable=True,
    )

    assert safe_error_from_provider_error(error) == {
        "code": "provider_rate_limited",
        "message": "Provider is temporarily rate-limited.",
        "retryable": True,
    }
