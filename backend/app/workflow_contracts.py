from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# internal workflows schemas

class DetectedProduct(BaseModel):
    label: str
    location_hint: str | None = Field(default=None, alias="locationHint")
    confidence: float = Field(ge=0, le=1)

    model_config = ConfigDict(populate_by_name=True)


class ImageGateResult(BaseModel):
    safety_status: Literal["safe", "unsafe"] = Field(alias="safetyStatus")
    product_suitability: Literal["single_product", "multiple_products", "non_product", "unclear"] = Field(
        alias="productSuitability"
    )
    product_likeness_confidence: float = Field(alias="productLikenessConfidence", ge=0, le=1)
    detected_products: list[DetectedProduct] = Field(default_factory=list, alias="detectedProducts")
    needs_clarification: bool = Field(default=False, alias="needsClarification")
    clarification_prompt: str | None = Field(default=None, alias="clarificationPrompt")
    injection_risk: Literal["low", "medium", "high"] = Field(default="low", alias="injectionRisk")
    instruction_like_text: list[str] = Field(default_factory=list, alias="instructionLikeText")
    decision: Literal["proceed", "needs_refinement", "fail_safe"]
    reason: str

    model_config = ConfigDict(populate_by_name=True)


class TargetProductSelection(BaseModel):
    decision: Literal["selected", "needs_refinement"]
    selected_product: DetectedProduct | None = Field(default=None, alias="selectedProduct")
    reason: str
    clarification_prompt: str | None = Field(default=None, alias="clarificationPrompt")

    model_config = ConfigDict(populate_by_name=True)


class ImageSafetyResult(BaseModel):
    safety_status: Literal["safe", "unsafe", "unclear"] = Field(alias="safetyStatus")
    unsafe_reasons: list[str] = Field(default_factory=list, alias="unsafeReasons")
    confidence: float = Field(ge=0, le=1)
    user_safe_message: str | None = Field(default=None, alias="userSafeMessage")

    model_config = ConfigDict(populate_by_name=True)


class TextSafetyResult(BaseModel):
    safety_status: Literal["safe", "unsafe", "unclear"] = Field(alias="safetyStatus")
    reason: str
    confidence: float = Field(ge=0, le=1)
    detected_patterns: list[str] = Field(default_factory=list, alias="detectedPatterns")
    user_safe_message: str | None = Field(default=None, alias="userSafeMessage")

    model_config = ConfigDict(populate_by_name=True)


class ProductReference(BaseModel):
    product_type: str = Field(alias="productType", min_length=1)
    title: str = Field(min_length=1)
    brand: str | None = None
    color: str | None = None
    materials: list[str] = Field(default_factory=list)
    key_features: list[str] = Field(default_factory=list, alias="keyFeatures")
    search_queries: list[str] = Field(default_factory=list, alias="searchQueries")
    confidence: float = Field(default=0.75, ge=0, le=1)
    assumptions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class ProductUnderstandingDecision(BaseModel):
    decision: Literal["extracted", "needs_refinement", "fail_safe"]
    product_reference: ProductReference | None = Field(default=None, alias="productReference")
    image_gate_result: ImageGateResult | None = Field(default=None, alias="imageGateResult")
    target_selection: TargetProductSelection | None = Field(default=None, alias="targetSelection")
    request_payload: dict[str, Any] = Field(default_factory=dict, alias="requestPayload")
    safe_error_code: str | None = Field(default=None, alias="safeErrorCode")
    user_safe_message: str | None = Field(default=None, alias="userSafeMessage")
    reason: str
    tool_calls: list[str] = Field(default_factory=list, alias="toolCalls")

    model_config = ConfigDict(populate_by_name=True)


class ProductContextCitation(BaseModel):
    title: str
    url: str | None = None
    source: str


class ProductContext(BaseModel):
    canonical_name: str | None = Field(default=None, alias="canonicalName")
    category_terms: list[str] = Field(default_factory=list, alias="categoryTerms")
    aliases: list[str] = Field(default_factory=list)
    feature_terms: list[str] = Field(default_factory=list, alias="featureTerms")
    material_terms: list[str] = Field(default_factory=list, alias="materialTerms")
    brand_or_model_hints: list[str] = Field(default_factory=list, alias="brandOrModelHints")
    exclusion_terms: list[str] = Field(default_factory=list, alias="exclusionTerms")
    source_citations: list[ProductContextCitation] = Field(default_factory=list, alias="sourceCitations")
    confidence: Literal["high", "medium", "low"] = "medium"
    uncertainty_notes: list[str] = Field(default_factory=list, alias="uncertaintyNotes")

    model_config = ConfigDict(populate_by_name=True)


class DiscoveryEngineRecommendation(BaseModel):
    engine: str
    priority: int = Field(default=1, ge=1)
    intent: str = "closest_match"
    reason: str


class QueryParamHint(BaseModel):
    engine: str
    params: dict[str, Any] = Field(default_factory=dict)
    intent: str = "closest_match"


class ProductDiscoveryProfile(BaseModel):
    product_family: Literal[
        "apparel",
        "electronics",
        "furniture",
        "home_goods",
        "home_improvement",
        "beauty_personal_care",
        "sports_outdoors",
        "toys_hobbies",
        "general",
    ] = Field(default="general", alias="productFamily")
    refined_product_type: str = Field(alias="refinedProductType", min_length=1)
    shopping_intent: str = Field(default="find_exact_or_similar", alias="shoppingIntent")
    consumer_decision_factors: list[str] = Field(default_factory=list, alias="consumerDecisionFactors")
    important_product_details: list[str] = Field(default_factory=list, alias="importantProductDetails")
    recommended_engines: list[str] = Field(default_factory=list, alias="recommendedEngines")
    engine_rationale: dict[str, str] = Field(default_factory=dict, alias="engineRationale")
    ranking_priorities: list[str] = Field(default_factory=list, alias="rankingPriorities")
    query_param_hints: list[QueryParamHint] = Field(default_factory=list, alias="queryParamHints")
    confidence: float = Field(default=0.65, ge=0, le=1)
    uncertainty_notes: list[str] = Field(default_factory=list, alias="uncertaintyNotes")

    model_config = ConfigDict(populate_by_name=True)


class ProductSearchContext(BaseModel):
    exact_terms: list[str] = Field(default_factory=list, alias="exactTerms")
    broad_terms: list[str] = Field(default_factory=list, alias="broadTerms")
    feature_terms: list[str] = Field(default_factory=list, alias="featureTerms")
    material_terms: list[str] = Field(default_factory=list, alias="materialTerms")
    style_terms: list[str] = Field(default_factory=list, alias="styleTerms")
    exclusion_terms: list[str] = Field(default_factory=list, alias="exclusionTerms")
    must_have_details: list[str] = Field(default_factory=list, alias="mustHaveDetails")
    optional_details: list[str] = Field(default_factory=list, alias="optionalDetails")
    source_notes: list[str] = Field(default_factory=list, alias="sourceNotes")

    model_config = ConfigDict(populate_by_name=True)


class ProductSearchPlanItem(BaseModel):
    engine: str
    params: dict[str, Any] = Field(default_factory=dict)
    intent: str = "closest_match"
    priority: int = Field(default=1, ge=1)
    reason: str | None = None


class ProductSearchPlan(BaseModel):
    plan_items: list[ProductSearchPlanItem] = Field(default_factory=list, alias="planItems")
    selected_engines: list[DiscoveryEngineRecommendation] = Field(default_factory=list, alias="selectedEngines")
    reasoning: str | None = None
    fallback_used: bool = Field(default=False, alias="fallbackUsed")

    model_config = ConfigDict(populate_by_name=True)


class DiscoverySourceError(BaseModel):
    engine: str
    code: str
    message: str
    retryable: bool = True


class ProductSearchRawResult(BaseModel):
    engine: str
    intent: str = "closest_match"
    params: dict[str, Any] = Field(default_factory=dict)
    response: Any = None


class ProductSearchExecutionResult(BaseModel):
    raw_results: list[ProductSearchRawResult] = Field(default_factory=list, alias="rawResults")
    source_errors: list[DiscoverySourceError] = Field(default_factory=list, alias="sourceErrors")

    model_config = ConfigDict(populate_by_name=True)


class ResearchQueryPlanItem(BaseModel):
    query: str = Field(min_length=1)
    purpose: Literal["exact_match", "alternative", "context", "verification"] = "exact_match"
    source: str = "serpapi-google-shopping"
    max_results: int = Field(default=10, ge=1, le=20, alias="maxResults")

    model_config = ConfigDict(populate_by_name=True)


class ResearchQueryPlan(BaseModel):
    queries: list[ResearchQueryPlanItem] = Field(default_factory=list)
    search_terms: list[str] = Field(default_factory=list, alias="searchTerms")
    exclusion_terms: list[str] = Field(default_factory=list, alias="exclusionTerms")
    source_preferences: list[str] = Field(default_factory=list, alias="sourcePreferences")
    reasoning: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class SourceProduct(BaseModel):
    source: str
    title: str
    retailer: str | None = None
    url: str | None = None
    price: float | None = Field(default=None, ge=0)
    currency: str = "USD"
    image_url: str | None = Field(default=None, alias="imageUrl")
    availability: str | None = None
    freshness: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class RankingScoreBreakdown(BaseModel):
    product_type_match: float = Field(default=0, ge=0, le=1, alias="productTypeMatch")
    brand_model_match: float = Field(default=0, ge=0, le=1, alias="brandModelMatch")
    visual_attribute_match: float = Field(default=0, ge=0, le=1, alias="visualAttributeMatch")
    feature_match: float = Field(default=0, ge=0, le=1, alias="featureMatch")
    material_color_style_match: float = Field(default=0, ge=0, le=1, alias="materialColorStyleMatch")
    price_preference_fit: float = Field(default=0, ge=0, le=1, alias="pricePreferenceFit")
    source_confidence: float = Field(default=0, ge=0, le=1, alias="sourceConfidence")
    availability_confidence: float = Field(default=0, ge=0, le=1, alias="availabilityConfidence")
    mismatch_penalty: float = Field(default=0, ge=0, le=1, alias="mismatchPenalty")
    final_score: float = Field(default=0, ge=0, le=1, alias="finalScore")

    model_config = ConfigDict(populate_by_name=True)


class CandidateMismatch(BaseModel):
    code: Literal[
        "wrong_category",
        "brand_conflict",
        "model_conflict",
        "material_conflict",
        "style_conflict",
        "missing_required_feature",
        "price_out_of_range",
        "weak_source_evidence",
    ]
    severity: Literal["low", "medium", "high"]
    message: str
    evidence: list[str] = Field(default_factory=list)


class RankedProduct(BaseModel):
    product: SourceProduct
    score: float = Field(ge=0, le=1)
    group: Literal["closest", "cheaper", "similar", "premium", "possible"]
    confidence: Literal["high", "medium", "low"]
    reason: str
    score_breakdown: RankingScoreBreakdown | None = Field(default=None, alias="scoreBreakdown")
    mismatches: list[CandidateMismatch] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class ProductResearchBrief(BaseModel):
    mode: str
    label: str
    product_reference: ProductReference = Field(alias="productReference")
    trust_summary: str = Field(alias="trustSummary")
    source_count: int = Field(alias="sourceCount", ge=0)
    freshness_note: str = Field(alias="freshnessNote")
    uncertainty_notes: list[str] = Field(default_factory=list, alias="uncertaintyNotes")
    ranked_products: list[RankedProduct] = Field(default_factory=list, alias="rankedProducts")
    ranking_explanation: dict[str, str] | None = Field(default=None, alias="rankingExplanation")
    user_actions: list[str] = Field(default_factory=list, alias="userActions")
    status_reason: str | None = Field(default=None, alias="statusReason")

    model_config = ConfigDict(populate_by_name=True)


class WorkflowProviderError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ExtractionOutputError(Exception):
    pass


class WorkflowResult(BaseModel):
    job_id: str = Field(alias="jobId")
    status: str

    model_config = ConfigDict(populate_by_name=True)


def model_dump_alias(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(by_alias=True)
