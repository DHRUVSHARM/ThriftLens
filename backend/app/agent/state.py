from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.workflow_contracts import (
    CandidateMismatch,
    ImageGateResult,
    ImageSafetyResult,
    ProductContext,
    ProductReference,
    ProductResearchBrief,
    RankedProduct,
    ResearchQueryPlan,
    SourceProduct,
    TextSafetyResult,
    WorkflowProviderError,
)


GraphNode = Literal[
    "start",
    "load_job_context",
    "prepare_artifacts",
    "route_by_input_type",
    "screen_text_safety",
    "decide_text_safety",
    "screen_image_safety",
    "decide_safety",
    "image_product_gate",
    "decide_product_gate",
    "extract_product_reference",
    "validate_reference",
    "repair_reference",
    "persist_reference",
    "enrich_product_context",
    "plan_product_search",
    "search_products",
    "normalize_sources",
    "score_candidates",
    "detect_mismatches",
    "group_candidates",
    "build_brief",
    "persist_final",
    "persist_partial",
    "persist_failure",
    "end",
]

PublicJobStatus = Literal[
    "queued",
    "extracting_reference",
    "needs_refinement",
    "researching_sources",
    "ranking_results",
    "complete",
    "partial",
    "failed",
    "expired",
]


class AgentIdentityState(BaseModel):
    job_id: str = Field(alias="jobId")
    provider_mode: str = Field(alias="providerMode")
    run_id: str | None = Field(default=None, alias="runId")

    model_config = ConfigDict(populate_by_name=True)


class AgentRequestState(BaseModel):
    input_type: Literal["image", "text"] = Field(alias="inputType")
    request_payload: dict[str, Any] = Field(default_factory=dict, alias="requestPayload")
    preferences: dict[str, Any] = Field(default_factory=dict)
    target_description: str | None = Field(default=None, alias="targetDescription")

    model_config = ConfigDict(populate_by_name=True)


class AgentArtifactState(BaseModel):
    image_metadata: list[dict[str, Any]] = Field(default_factory=list, alias="imageMetadata")
    image_object_key: str | None = Field(default=None, alias="imageObjectKey")
    image_checksum: str | None = Field(default=None, alias="imageChecksum")

    model_config = ConfigDict(populate_by_name=True)


class AgentSafetyState(BaseModel):
    image_safety_result: ImageSafetyResult | None = Field(default=None, alias="imageSafetyResult")
    text_safety_result: TextSafetyResult | None = Field(default=None, alias="textSafetyResult")
    safety_decision: Literal["proceed", "needs_refinement", "fail_safe"] | None = Field(
        default=None,
        alias="safetyDecision",
    )

    model_config = ConfigDict(populate_by_name=True)


class AgentGateState(BaseModel):
    image_gate_result: ImageGateResult | None = Field(default=None, alias="imageGateResult")
    gate_decision: Literal["proceed", "needs_refinement", "fail_safe"] | None = Field(
        default=None,
        alias="gateDecision",
    )
    refinement_prompt: str | None = Field(default=None, alias="refinementPrompt")

    model_config = ConfigDict(populate_by_name=True)


class AgentReferenceState(BaseModel):
    product_reference: ProductReference | None = Field(default=None, alias="productReference")
    validation_errors: list[str] = Field(default_factory=list, alias="validationErrors")
    repair_attempted: bool = Field(default=False, alias="repairAttempted")

    model_config = ConfigDict(populate_by_name=True)


class AgentContextState(BaseModel):
    product_context: ProductContext | None = Field(default=None, alias="productContext")
    context_sources: list[dict[str, Any]] = Field(default_factory=list, alias="contextSources")
    context_uncertainty_notes: list[str] = Field(default_factory=list, alias="contextUncertaintyNotes")

    model_config = ConfigDict(populate_by_name=True)


class AgentResearchState(BaseModel):
    query_plan: ResearchQueryPlan | None = Field(default=None, alias="queryPlan")
    source_products: list[SourceProduct] = Field(default_factory=list, alias="sourceProducts")
    source_errors: list[dict[str, Any]] = Field(default_factory=list, alias="sourceErrors")
    source_verification: list[dict[str, Any]] = Field(default_factory=list, alias="sourceVerification")

    model_config = ConfigDict(populate_by_name=True)


class AgentRankingState(BaseModel):
    ranked_products: list[RankedProduct] = Field(default_factory=list, alias="rankedProducts")
    score_breakdowns: dict[str, dict[str, Any]] = Field(default_factory=dict, alias="scoreBreakdowns")
    mismatch_flags: dict[str, list[CandidateMismatch]] = Field(default_factory=dict, alias="mismatchFlags")
    ranking_explanations: dict[str, str] = Field(default_factory=dict, alias="rankingExplanations")

    model_config = ConfigDict(populate_by_name=True)


class AgentBriefState(BaseModel):
    partial_brief: ProductResearchBrief | None = Field(default=None, alias="partialBrief")
    final_brief: ProductResearchBrief | None = Field(default=None, alias="finalBrief")

    model_config = ConfigDict(populate_by_name=True)


class AgentControlState(BaseModel):
    current_node: GraphNode = Field(default="start", alias="currentNode")
    public_status: PublicJobStatus = Field(default="queued", alias="publicStatus")
    progress_message: str = Field(default="Research queued.", alias="progressMessage")
    retryable: bool = False
    safe_error: dict[str, Any] | None = Field(default=None, alias="safeError")
    terminal: bool = False
    tool_call_count: int = Field(default=0, ge=0, alias="toolCallCount")

    model_config = ConfigDict(populate_by_name=True)


class AgentTraceState(BaseModel):
    redacted_node_events: list[dict[str, Any]] = Field(default_factory=list, alias="redactedNodeEvents")
    redacted_tool_calls: list[dict[str, Any]] = Field(default_factory=list, alias="redactedToolCalls")
    dependency_events: list[dict[str, Any]] = Field(default_factory=list, alias="dependencyEvents")

    model_config = ConfigDict(populate_by_name=True)


class ProductResearchAgentState(BaseModel):
    identity: AgentIdentityState
    request: AgentRequestState
    artifacts: AgentArtifactState = Field(default_factory=AgentArtifactState)
    safety: AgentSafetyState = Field(default_factory=AgentSafetyState)
    gate: AgentGateState = Field(default_factory=AgentGateState)
    reference: AgentReferenceState = Field(default_factory=AgentReferenceState)
    context: AgentContextState = Field(default_factory=AgentContextState)
    research: AgentResearchState = Field(default_factory=AgentResearchState)
    ranking: AgentRankingState = Field(default_factory=AgentRankingState)
    brief: AgentBriefState = Field(default_factory=AgentBriefState)
    control: AgentControlState = Field(default_factory=AgentControlState)
    trace: AgentTraceState = Field(default_factory=AgentTraceState)

    model_config = ConfigDict(populate_by_name=True)


def safe_error_from_provider_error(error: WorkflowProviderError) -> dict[str, Any]:
    return {
        "code": error.code,
        "message": str(error),
        "retryable": error.retryable,
    }
