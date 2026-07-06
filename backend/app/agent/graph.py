import logging
from collections.abc import Callable
from typing import Any, TypedDict

from pydantic import ValidationError
from langgraph.graph import END, START, StateGraph

from app.agent.product_understanding import ProductUnderstandingAgent
from app.job_repository import (
    get_research_job,
    get_uploaded_images,
    mark_job_failed,
    mark_job_needs_refinement,
    record_job_attempt,
    store_final_brief,
    store_partial_brief,
    store_product_reference,
    update_dependency_health,
    update_job_stage,
)
from app.mcp_servers.extraction.client import ExtractionToolClientProtocol
from app.mcp_servers.discovery.client import DiscoveryToolClientProtocol
from app.mcp_servers.ranking.client import RankingToolClientProtocol
from app.product_safety import is_regulated_product_reference, is_searchable_product_reference
from app.ranking import deterministic_rank, detect_ranked_mismatches, explain_ranked_products, group_ranked_products
from app.workflow import safe_input_gate_message, safe_provider_message
from app.workflow_contracts import (
    ImageSafetyResult,
    ProductDiscoveryProfile,
    ProductReference,
    ProductResearchBrief,
    ProductSearchContext,
    ProductSearchExecutionResult,
    ProductSearchPlan,
    ProductUnderstandingDecision,
    RankedProduct,
    SourceProduct,
    TextSafetyResult,
    WorkflowProviderError,
    WorkflowResult,
    model_dump_alias,
)


ExtractionClientFactory = Callable[[], ExtractionToolClientProtocol]
DiscoveryClientFactory = Callable[[], DiscoveryToolClientProtocol]
RankingClientFactory = Callable[[], RankingToolClientProtocol]
logger = logging.getLogger(__name__)


class AgentGraphRuntimeState(TypedDict, total=False):
    job_id: str
    job: dict[str, Any] | None
    image_metadata: list[dict[str, Any]]
    input_type: str
    request_payload: dict[str, Any]
    image_safety_result: dict[str, Any]
    text_safety_result: dict[str, Any]
    product_understanding: dict[str, Any]
    product_reference: dict[str, Any]
    product_discovery_profile: dict[str, Any]
    product_search_context: dict[str, Any]
    product_search_plan: dict[str, Any]
    product_search_results: dict[str, Any]
    source_products: list[dict[str, Any]]
    ranked_products: list[dict[str, Any]]
    ranking_explanation: dict[str, str]
    workflow_result: dict[str, Any]


async def load_job_context_node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
    job_id = state["job_id"]
    job = await get_research_job(job_id)
    image_metadata = await get_uploaded_images(job_id) if job is not None else []
    return {
        "job": job,
        "image_metadata": image_metadata,
    }


def route_after_load(state: AgentGraphRuntimeState) -> str:
    if state.get("job") is None:
        return "missing_job"
    return "prepare_artifacts"


async def missing_job_node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
    return {
        "workflow_result": WorkflowResult(
            jobId=state["job_id"],
            status="missing",
        ).model_dump(by_alias=True)
    }


async def prepare_artifacts_node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
    job = state["job"] or {}
    request_payload = dict(job.get("request_payload") or {})
    input_type = job.get("input_type") or request_payload.get("inputType") or "text"
    await update_job_stage(
        state["job_id"],
        status="extracting_reference",
        progress_message="Extracting product reference.",
    )
    return {
        "input_type": input_type,
        "request_payload": request_payload,
    }


def route_by_input_type(state: AgentGraphRuntimeState) -> str:
    if state.get("input_type") == "text" or _has_user_text(state.get("request_payload") or {}):
        return "screen_text_safety"
    if state.get("input_type") == "image":
        return "screen_image_safety"
    return "extract_product_reference"


def screen_text_safety_node(extraction_client_factory: ExtractionClientFactory):
    async def node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
        job_id = state["job_id"]
        await update_job_stage(job_id, status="extracting_reference", progress_message="Screening product description.")
        await record_job_attempt(job_id=job_id, stage="screenTextSafety", dependency="extraction-mcp", attempt=1)
        try:
            safety = await extraction_client_factory().screen_text_safety(
                request_payload=state.get("request_payload") or {},
            )
            return {"text_safety_result": model_dump_alias(safety)}
        except WorkflowProviderError as exc:
            return await _fail_provider_job(job_id, exc, stage="screenTextSafety")

    return node


def route_after_text_safety(state: AgentGraphRuntimeState) -> str:
    if state.get("workflow_result"):
        return "end"
    safety = TextSafetyResult.model_validate(state.get("text_safety_result") or {})
    if safety.safety_status == "unsafe":
        return "fail_unsafe_text"
    if safety.safety_status == "unclear":
        return "refine_text_input"
    if state.get("input_type") == "image":
        return "screen_image_safety"
    return "extract_product_reference"


async def fail_unsafe_text_node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
    job_id = state["job_id"]
    safety = TextSafetyResult.model_validate(state.get("text_safety_result") or {})
    code = "regulated_product" if safety.reason == "regulated_product" else "unsafe_text"
    await mark_job_failed(
        job_id,
        code=code,
        message=safety.user_safe_message or safe_input_gate_message(code),
        retryable=False,
    )
    return {"workflow_result": WorkflowResult(jobId=job_id, status="failed").model_dump(by_alias=True)}


async def refine_text_input_node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
    job_id = state["job_id"]
    safety = TextSafetyResult.model_validate(state.get("text_safety_result") or {})
    code = _text_safety_code(safety)
    await mark_job_needs_refinement(
        job_id,
        code=code,
        message=safety.user_safe_message or safe_input_gate_message(code),
    )
    return {"workflow_result": WorkflowResult(jobId=job_id, status="needs_refinement").model_dump(by_alias=True)}


def screen_image_safety_node(extraction_client_factory: ExtractionClientFactory):
    async def node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
        job_id = state["job_id"]
        await update_job_stage(job_id, status="extracting_reference", progress_message="Screening image safety.")
        await record_job_attempt(job_id=job_id, stage="screenImageSafety", dependency="extraction-mcp", attempt=1)
        try:
            safety = await extraction_client_factory().screen_image_safety(
                request_payload=state.get("request_payload") or {},
                image_metadata=state.get("image_metadata") or [],
            )
            return {"image_safety_result": model_dump_alias(safety)}
        except WorkflowProviderError as exc:
            return await _fail_provider_job(job_id, exc, stage="screenImageSafety")

    return node


def route_after_safety(state: AgentGraphRuntimeState) -> str:
    if state.get("workflow_result"):
        return "end"
    safety = ImageSafetyResult.model_validate(state.get("image_safety_result") or {})
    if safety.safety_status == "unsafe":
        return "fail_unsafe_image"
    if safety.safety_status == "unclear":
        return "refine_ambiguous_image"
    return "understand_image_product"


async def fail_unsafe_image_node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
    job_id = state["job_id"]
    safety = ImageSafetyResult.model_validate(state.get("image_safety_result") or {})
    await mark_job_failed(
        job_id,
        code="unsafe_image",
        message=safety.user_safe_message or safe_input_gate_message("unsafe_image"),
        retryable=False,
    )
    return {"workflow_result": WorkflowResult(jobId=job_id, status="failed").model_dump(by_alias=True)}


async def refine_ambiguous_image_node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
    job_id = state["job_id"]
    safety = ImageSafetyResult.model_validate(state.get("image_safety_result") or {})
    await mark_job_needs_refinement(
        job_id,
        code="image_safety_unclear",
        message=safety.user_safe_message or safe_input_gate_message("image_safety_unclear"),
    )
    return {"workflow_result": WorkflowResult(jobId=job_id, status="needs_refinement").model_dump(by_alias=True)}


def understand_image_product_node(extraction_client_factory: ExtractionClientFactory):
    async def node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
        job_id = state["job_id"]
        await update_job_stage(job_id, status="extracting_reference", progress_message="Checking product clarity.")
        await record_job_attempt(job_id=job_id, stage="understandProduct", dependency="extraction-mcp", attempt=1)
        try:
            decision = await ProductUnderstandingAgent(extraction_client=extraction_client_factory()).run(
                input_type="image",
                request_payload=state.get("request_payload") or {},
                image_metadata=state.get("image_metadata") or [],
            )
            if decision.decision == "extracted" and decision.product_reference is None:
                raise WorkflowProviderError(
                    "product_understanding_missing_reference",
                    "Product understanding completed without enough product detail.",
                    retryable=True,
                )
            payload = model_dump_alias(decision)
            result: AgentGraphRuntimeState = {
                "product_understanding": payload,
                "request_payload": payload.get("requestPayload") or state.get("request_payload") or {},
            }
            if decision.product_reference is not None:
                result["product_reference"] = model_dump_alias(decision.product_reference)
            return result
        except WorkflowProviderError as exc:
            return await _fail_provider_job(job_id, exc, stage="understandProduct")
        except Exception as exc:
            logger.exception("Product understanding failed unexpectedly for job %s", job_id)
            return await _fail_provider_job(
                job_id,
                WorkflowProviderError(
                    "product_understanding_unexpected_error",
                    "Product understanding failed unexpectedly. Try again shortly.",
                    retryable=True,
                ),
                stage="understandProduct",
            )

    return node


def route_after_product_understanding(state: AgentGraphRuntimeState) -> str:
    if state.get("workflow_result"):
        return "end"
    decision = ProductUnderstandingDecision.model_validate(state.get("product_understanding") or {})
    if decision.decision == "fail_safe":
        return "fail_product_understanding"
    if decision.decision == "needs_refinement":
        return "refine_product_understanding"
    if decision.product_reference is not None and is_regulated_product_reference(decision.product_reference):
        return "fail_regulated_product_reference"
    if decision.product_reference is not None and not is_searchable_product_reference(decision.product_reference):
        return "refine_non_product_reference"
    if decision.product_reference is None:
        return "refine_product_understanding"
    return "persist_reference"


async def fail_product_understanding_node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
    job_id = state["job_id"]
    decision = ProductUnderstandingDecision.model_validate(state.get("product_understanding") or {})
    code = decision.safe_error_code or "ambiguous_image"
    await mark_job_failed(
        job_id,
        code=code,
        message=decision.user_safe_message or safe_input_gate_message(code),
        retryable=False,
    )
    return {"workflow_result": WorkflowResult(jobId=job_id, status="failed").model_dump(by_alias=True)}


async def refine_product_understanding_node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
    job_id = state["job_id"]
    decision = ProductUnderstandingDecision.model_validate(state.get("product_understanding") or {})
    code = decision.safe_error_code or "ambiguous_image"
    await mark_job_needs_refinement(job_id, code=code, message=decision.user_safe_message or safe_input_gate_message(code))
    return {"workflow_result": WorkflowResult(jobId=job_id, status="needs_refinement").model_dump(by_alias=True)}


def extract_product_reference_node(extraction_client_factory: ExtractionClientFactory):
    async def node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
        job_id = state["job_id"]
        request_payload = dict(state.get("request_payload") or {})

        await update_job_stage(job_id, status="extracting_reference", progress_message="Extracting product reference.")
        await record_job_attempt(job_id=job_id, stage="extractReference", dependency="extraction-mcp", attempt=1)
        try:
            reference = await extraction_client_factory().extract_product_reference(
                input_type=state.get("input_type") or "text",
                request_payload=request_payload,
                image_metadata=state.get("image_metadata") or [],
            )
            return {
                "request_payload": request_payload,
                "product_reference": model_dump_alias(reference),
            }
        except WorkflowProviderError as exc:
            return await _fail_provider_job(job_id, exc, stage="extractReference")
        except ValidationError:
            await mark_job_failed(
                job_id,
                code="reference_extraction_failed",
                message="We could not extract enough product detail. Try a clearer image or more specific description.",
                retryable=True,
            )
            return {"workflow_result": WorkflowResult(jobId=job_id, status="failed").model_dump(by_alias=True)}

    return node


def route_after_reference(state: AgentGraphRuntimeState) -> str:
    if state.get("workflow_result"):
        return "end"
    reference = ProductReference.model_validate(state["product_reference"])
    if is_regulated_product_reference(reference):
        return "fail_regulated_product_reference"
    if not is_searchable_product_reference(reference):
        return "refine_non_product_reference"
    return "persist_reference"


def route_after_discovery_stage(state: AgentGraphRuntimeState) -> str:
    if state.get("workflow_result"):
        return "end"
    return "continue"


async def persist_reference_node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
    job_id = state["job_id"]
    reference = ProductReference.model_validate(state["product_reference"])
    await store_product_reference(
        job_id,
        product_reference=model_dump_alias(reference),
        progress_message="Product reference extracted.",
    )
    await update_dependency_health(dependency="extraction-mcp", state="healthy")
    return {}


async def fail_regulated_product_reference_node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
    job_id = state["job_id"]
    await mark_job_failed(
        job_id,
        code="regulated_product",
        message=safe_input_gate_message("regulated_product"),
        retryable=False,
    )
    return {"workflow_result": WorkflowResult(jobId=job_id, status="failed").model_dump(by_alias=True)}


async def refine_non_product_reference_node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
    job_id = state["job_id"]
    await mark_job_needs_refinement(
        job_id,
        code="text_not_product",
        message=safe_input_gate_message("text_not_product"),
    )
    return {"workflow_result": WorkflowResult(jobId=job_id, status="needs_refinement").model_dump(by_alias=True)}


def classify_product_profile_node(discovery_client_factory: DiscoveryClientFactory):
    async def node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
        job_id = state["job_id"]
        reference = ProductReference.model_validate(state["product_reference"])
        preferences = ((state.get("request_payload") or {}).get("researchPreferences") or {})
        await update_job_stage(job_id, status="researching_sources", progress_message="Understanding product search strategy.")
        await record_job_attempt(job_id=job_id, stage="classifyProductProfile", dependency="discovery-mcp", attempt=1)
        try:
            profile = await discovery_client_factory().classify_product_profile(
                product_reference=reference,
                preferences=preferences,
            )
            return {"product_discovery_profile": model_dump_alias(profile)}
        except WorkflowProviderError as exc:
            return await _partial_discovery_job(job_id, reference, exc, stage="classifyProductProfile")

    return node


def build_search_context_node(discovery_client_factory: DiscoveryClientFactory):
    async def node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
        job_id = state["job_id"]
        reference = ProductReference.model_validate(state["product_reference"])
        profile = ProductDiscoveryProfile.model_validate(state["product_discovery_profile"])
        await update_job_stage(job_id, status="researching_sources", progress_message="Building source search context.")
        await record_job_attempt(job_id=job_id, stage="buildSearchContext", dependency="discovery-mcp", attempt=1)
        try:
            context = await discovery_client_factory().build_search_context(
                product_reference=reference,
                product_profile=profile,
            )
            return {"product_search_context": model_dump_alias(context)}
        except WorkflowProviderError as exc:
            return await _partial_discovery_job(job_id, reference, exc, stage="buildSearchContext")

    return node


def plan_search_sources_node(discovery_client_factory: DiscoveryClientFactory):
    async def node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
        job_id = state["job_id"]
        reference = ProductReference.model_validate(state["product_reference"])
        profile = ProductDiscoveryProfile.model_validate(state["product_discovery_profile"])
        context = ProductSearchContext.model_validate(state["product_search_context"])
        preferences = ((state.get("request_payload") or {}).get("researchPreferences") or {})
        await update_job_stage(job_id, status="researching_sources", progress_message="Planning source searches.")
        await record_job_attempt(job_id=job_id, stage="planSearchSources", dependency="discovery-mcp", attempt=1)
        try:
            plan = await discovery_client_factory().plan_search_sources(
                product_reference=reference,
                product_profile=profile,
                search_context=context,
                preferences=preferences,
            )
            return {"product_search_plan": model_dump_alias(plan)}
        except WorkflowProviderError as exc:
            return await _partial_discovery_job(job_id, reference, exc, stage="planSearchSources")

    return node


def execute_search_plan_node(discovery_client_factory: DiscoveryClientFactory):
    async def node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
        job_id = state["job_id"]
        reference = ProductReference.model_validate(state["product_reference"])
        plan = ProductSearchPlan.model_validate(state["product_search_plan"])
        await update_job_stage(job_id, status="researching_sources", progress_message="Searching source-backed products.")
        await record_job_attempt(
            job_id=job_id,
            stage="executeSearchPlan",
            dependency="discovery-mcp",
            attempt=1,
            metadata={
                "plannedCallCount": len(plan.plan_items),
                "plannedEngines": [item.engine for item in plan.plan_items],
                "plannedIntents": [item.intent for item in plan.plan_items],
            },
        )
        try:
            results = await discovery_client_factory().execute_search_plan(search_plan=plan)
            if not results.raw_results and results.source_errors:
                error = results.source_errors[0]
                return await _partial_discovery_job(
                    job_id,
                    reference,
                    WorkflowProviderError(error.code, error.message, retryable=error.retryable),
                    stage="executeSearchPlan",
                )
            return {"product_search_results": model_dump_alias(results)}
        except WorkflowProviderError as exc:
            return await _partial_discovery_job(job_id, reference, exc, stage="executeSearchPlan")

    return node


def normalize_products_node(discovery_client_factory: DiscoveryClientFactory):
    async def node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
        job_id = state["job_id"]
        reference = ProductReference.model_validate(state["product_reference"])
        results = ProductSearchExecutionResult.model_validate(state.get("product_search_results") or {})
        await update_job_stage(job_id, status="researching_sources", progress_message="Normalizing source results.")
        await record_job_attempt(
            job_id=job_id,
            stage="normalizeProducts",
            dependency="discovery-mcp",
            attempt=1,
            metadata={"rawResultCount": len(results.raw_results), "sourceErrorCount": len(results.source_errors)},
        )
        try:
            products = await discovery_client_factory().normalize_products(search_results=results)
            await update_dependency_health(dependency="discovery-mcp", state="healthy")
            return {"source_products": [model_dump_alias(product) for product in products]}
        except WorkflowProviderError as exc:
            return await _partial_discovery_job(job_id, reference, exc, stage="normalizeProducts")

    return node


def score_candidates_node(ranking_client_factory: RankingClientFactory):
    async def node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
        job_id = state["job_id"]
        reference = ProductReference.model_validate(state["product_reference"])
        profile = ProductDiscoveryProfile.model_validate(state["product_discovery_profile"])
        context = ProductSearchContext.model_validate(state["product_search_context"])
        products = [SourceProduct.model_validate(product) for product in state.get("source_products") or []]
        preferences = ((state.get("request_payload") or {}).get("researchPreferences") or {})
        await update_job_stage(job_id, status="ranking_results", progress_message="Scoring source-backed candidates.")
        await record_job_attempt(
            job_id=job_id,
            stage="scoreCandidates",
            dependency="ranking-mcp",
            attempt=1,
            metadata={"sourceProductCount": len(products)},
        )
        try:
            ranked = await ranking_client_factory().score_candidates(
                product_reference=reference,
                product_profile=profile,
                search_context=context,
                source_products=products,
                preferences=preferences,
            )
            await update_dependency_health(dependency="ranking-mcp", state="healthy")
            return {"ranked_products": [model_dump_alias(product) for product in ranked]}
        except WorkflowProviderError as exc:
            return await _fallback_ranking_job(
                state,
                exc,
                stage="scoreCandidates",
                reason="Ranking server unavailable; deterministic fallback scored the candidates.",
            )

    return node


def detect_mismatches_node(ranking_client_factory: RankingClientFactory):
    async def node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
        job_id = state["job_id"]
        reference = ProductReference.model_validate(state["product_reference"])
        profile = ProductDiscoveryProfile.model_validate(state["product_discovery_profile"])
        context = ProductSearchContext.model_validate(state["product_search_context"])
        ranked_products = [RankedProduct.model_validate(product) for product in state.get("ranked_products") or []]
        await update_job_stage(job_id, status="ranking_results", progress_message="Checking candidate mismatches.")
        await record_job_attempt(
            job_id=job_id,
            stage="detectMismatches",
            dependency="ranking-mcp",
            attempt=1,
            metadata={"candidateCount": len(ranked_products)},
        )
        try:
            ranked = await ranking_client_factory().detect_mismatches(
                product_reference=reference,
                product_profile=profile,
                search_context=context,
                ranked_products=ranked_products,
            )
            return {"ranked_products": [model_dump_alias(product) for product in ranked]}
        except WorkflowProviderError as exc:
            await _record_ranking_fallback(job_id, exc, stage="detectMismatches")
            fallback = detect_ranked_mismatches(
                product_reference=reference,
                product_profile=profile,
                search_context=context,
                ranked_products=ranked_products,
            )
            return {"ranked_products": [model_dump_alias(product) for product in fallback]}

    return node


def group_candidates_node(ranking_client_factory: RankingClientFactory):
    async def node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
        job_id = state["job_id"]
        ranked_products = [RankedProduct.model_validate(product) for product in state.get("ranked_products") or []]
        preferences = ((state.get("request_payload") or {}).get("researchPreferences") or {})
        await update_job_stage(job_id, status="ranking_results", progress_message="Grouping alternatives.")
        await record_job_attempt(
            job_id=job_id,
            stage="groupCandidates",
            dependency="ranking-mcp",
            attempt=1,
            metadata={"candidateCount": len(ranked_products)},
        )
        try:
            grouped = await ranking_client_factory().group_candidates(
                ranked_products=ranked_products,
                preferences=preferences,
            )
            return {"ranked_products": [model_dump_alias(product) for product in grouped]}
        except WorkflowProviderError as exc:
            await _record_ranking_fallback(job_id, exc, stage="groupCandidates")
            fallback = group_ranked_products(ranked_products=ranked_products, preferences=preferences)
            return {"ranked_products": [model_dump_alias(product) for product in fallback]}

    return node


def explain_ranking_node(ranking_client_factory: RankingClientFactory):
    async def node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
        job_id = state["job_id"]
        reference = ProductReference.model_validate(state["product_reference"])
        profile = ProductDiscoveryProfile.model_validate(state["product_discovery_profile"])
        context = ProductSearchContext.model_validate(state["product_search_context"])
        ranked_products = [RankedProduct.model_validate(product) for product in state.get("ranked_products") or []]
        await update_job_stage(job_id, status="ranking_results", progress_message="Preparing ranking explanations.")
        await record_job_attempt(
            job_id=job_id,
            stage="explainRanking",
            dependency="ranking-mcp",
            attempt=1,
            metadata={"candidateCount": len(ranked_products)},
        )
        try:
            explanation = await ranking_client_factory().explain_match(
                product_reference=reference,
                product_profile=profile,
                search_context=context,
                ranked_products=ranked_products,
            )
            explanation = {**(state.get("ranking_explanation") or {}), **explanation}
            return {"ranking_explanation": explanation}
        except WorkflowProviderError as exc:
            await _record_ranking_fallback(job_id, exc, stage="explainRanking")
            fallback = explain_ranked_products(
                product_reference=reference,
                product_profile=profile,
                search_context=context,
                ranked_products=ranked_products,
            )
            return {"ranking_explanation": {**(state.get("ranking_explanation") or {}), **fallback}}

    return node


async def persist_final_brief_node(state: AgentGraphRuntimeState) -> AgentGraphRuntimeState:
    job_id = state["job_id"]
    reference = ProductReference.model_validate(state["product_reference"])
    profile = ProductDiscoveryProfile.model_validate(state["product_discovery_profile"])
    context = ProductSearchContext.model_validate(state["product_search_context"])
    plan = ProductSearchPlan.model_validate(state["product_search_plan"])
    ranked_products = [model for model in state.get("ranked_products") or []]
    brief = _build_final_brief(
        reference,
        ranked_products,
        state.get("ranking_explanation"),
        product_profile=profile,
        search_context=context,
        search_plan=plan,
    )
    final_job = await store_final_brief(
        job_id,
        final_brief=model_dump_alias(brief),
        status="complete",
        progress_message="Research brief complete.",
    )
    return {"workflow_result": WorkflowResult(jobId=job_id, status=final_job["status"] if final_job else "complete").model_dump(by_alias=True)}


async def _fallback_ranking_job(
    state: AgentGraphRuntimeState,
    exc: WorkflowProviderError,
    *,
    stage: str,
    reason: str,
) -> AgentGraphRuntimeState:
    job_id = state["job_id"]
    await _record_ranking_fallback(job_id, exc, stage=stage)
    reference = ProductReference.model_validate(state["product_reference"])
    products = [SourceProduct.model_validate(product) for product in state.get("source_products") or []]
    ranked = deterministic_rank(reference, products)
    explanation = explain_ranked_products(
        product_reference=reference,
        product_profile=ProductDiscoveryProfile.model_validate(state["product_discovery_profile"]),
        search_context=ProductSearchContext.model_validate(state["product_search_context"]),
        ranked_products=ranked,
    )
    explanation["fallback"] = reason
    return {
        "ranked_products": [model_dump_alias(product) for product in ranked],
        "ranking_explanation": explanation,
    }


async def _record_ranking_fallback(job_id: str, exc: WorkflowProviderError, *, stage: str) -> None:
    await record_job_attempt(
        job_id=job_id,
        stage=stage,
        dependency="ranking-mcp",
        attempt=2,
        error_code=exc.code,
        retryable=exc.retryable,
        metadata={"fallback": "deterministic-ranking"},
    )
    await update_dependency_health(dependency="ranking-mcp", state="degraded", failure=True)


async def _fail_provider_job(job_id: str, exc: WorkflowProviderError, *, stage: str) -> AgentGraphRuntimeState:
    await record_job_attempt(
        job_id=job_id,
        stage=stage,
        dependency="extraction-mcp",
        attempt=2,
        error_code=exc.code,
        retryable=exc.retryable,
    )
    await mark_job_failed(
        job_id,
        code=exc.code,
        message=safe_provider_message(exc.code),
        retryable=exc.retryable,
    )
    return {"workflow_result": WorkflowResult(jobId=job_id, status="failed").model_dump(by_alias=True)}


async def _partial_discovery_job(
    job_id: str,
    reference: ProductReference,
    exc: WorkflowProviderError,
    *,
    stage: str,
) -> AgentGraphRuntimeState:
    await record_job_attempt(
        job_id=job_id,
        stage=stage,
        dependency="discovery-mcp",
        attempt=2,
        error_code=exc.code,
        retryable=exc.retryable,
    )
    await update_dependency_health(dependency="discovery-mcp", state="degraded", failure=True)
    partial = _build_research_unavailable_brief(reference, exc.code)
    await store_partial_brief(
        job_id,
        partial_brief=model_dump_alias(partial),
        status="partial",
        progress_message="Product reference extracted, but research sources are unavailable.",
        retryable=exc.retryable,
    )
    return {"workflow_result": WorkflowResult(jobId=job_id, status="partial").model_dump(by_alias=True)}


def _build_research_unavailable_brief(reference: ProductReference, code: str) -> ProductResearchBrief:
    return ProductResearchBrief(
        mode="sample",
        label="Sample/static result",
        productReference=reference,
        trustSummary="Reference extracted, but source-backed research is unavailable.",
        sourceCount=0,
        freshnessNote="No source data was available for this run.",
        uncertaintyNotes=[code, "Try again when research sources are available."],
        rankedProducts=[],
        userActions=["Retry research", "Refine the product reference"],
        statusReason="research_unavailable",
    )


def _build_final_brief(
    reference: ProductReference,
    ranked_products: list[dict[str, Any]],
    ranking_explanation: dict[str, str] | None = None,
    *,
    product_profile: ProductDiscoveryProfile | None = None,
    search_context: ProductSearchContext | None = None,
    search_plan: ProductSearchPlan | None = None,
) -> ProductResearchBrief:
    has_verified = any(product.get("group") == "closest" and product.get("score", 0) >= 0.74 for product in ranked_products)
    notes = _build_evidence_notes(
        reference,
        product_profile=product_profile,
        search_context=search_context,
        search_plan=search_plan,
    )
    if not has_verified:
        notes.append("No exact match was verified; these are the closest available alternatives from the sources checked.")
    if len(ranked_products) <= 1:
        notes.append("Only one source-backed candidate was available for this run. Refine the evidence or retry to broaden the comparison.")

    return ProductResearchBrief(
        mode="source-backed",
        label="Source-backed result",
        productReference=reference,
        trustSummary=_build_trust_summary(reference, has_verified=has_verified, product_profile=product_profile),
        sourceCount=len(ranked_products),
        freshnessNote="Prices and availability come from the latest source response and may change.",
        uncertaintyNotes=notes,
        rankedProducts=ranked_products,
        rankingExplanation=ranking_explanation,
        userActions=["Review matches", "Refine description", "Retry research"],
        statusReason=None if has_verified else "possible_matches_only",
    )


def _build_trust_summary(
    reference: ProductReference,
    *,
    has_verified: bool,
    product_profile: ProductDiscoveryProfile | None,
) -> str:
    profile_label = product_profile.refined_product_type if product_profile else reference.product_type
    family = product_profile.product_family.replace("_", " ") if product_profile else "product"
    factors = _brief_terms(product_profile.consumer_decision_factors if product_profile else [], limit=4)
    factor_text = f" using {', '.join(factors)}" if factors else ""
    if has_verified:
        return f"Found source-backed {profile_label} matches after classifying this as {family}{factor_text}."
    return f"Found source-backed {profile_label} alternatives after classifying this as {family}{factor_text}; no exact match was verified."


def _build_evidence_notes(
    reference: ProductReference,
    *,
    product_profile: ProductDiscoveryProfile | None,
    search_context: ProductSearchContext | None,
    search_plan: ProductSearchPlan | None,
) -> list[str]:
    notes: list[str] = []
    if product_profile:
        priorities = _brief_terms(product_profile.ranking_priorities or product_profile.consumer_decision_factors, limit=5)
        if priorities:
            notes.append(f"Ranking prioritized shopper signals for this product type: {', '.join(priorities)}.")
    context_terms = _brief_terms(
        [
            *(search_context.must_have_details if search_context else []),
            *(search_context.material_terms if search_context else []),
            *(search_context.feature_terms if search_context else []),
        ],
        limit=6,
    )
    if context_terms:
        notes.append(f"Search and ranking used these extracted details as evidence: {', '.join(context_terms)}.")
    elif reference.key_features:
        notes.append(f"Search and ranking used extracted features: {', '.join(_brief_terms(reference.key_features, limit=5))}.")
    if search_plan and search_plan.plan_items:
        strategy = _search_strategy_note(search_plan)
        if strategy:
            notes.append(strategy)
    return notes or ["Matches are based on live source results and the product details extracted from your evidence."]


def _search_strategy_note(search_plan: ProductSearchPlan) -> str | None:
    labels = []
    for item in search_plan.plan_items:
        engine = item.engine.replace("_", " ")
        intent = item.intent.replace("_", " ")
        labels.append(f"{engine} for {intent}")
    if not labels:
        return None
    return f"Research ran {', '.join(_brief_terms(labels, limit=4))}."


def _brief_terms(values: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    terms: list[str] = []
    for value in values:
        normalized = str(value).strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        terms.append(normalized)
        if len(terms) >= limit:
            break
    return terms


def _has_user_text(request_payload: dict[str, Any]) -> bool:
    return any(
        isinstance(request_payload.get(key), str) and bool(request_payload.get(key, "").strip())
        for key in ("textDescription", "targetDescription")
    )


def _text_safety_code(safety: TextSafetyResult) -> str:
    if safety.reason == "prompt_injection":
        return "text_prompt_injection"
    if safety.reason == "non_product_request":
        return "text_not_product"
    if safety.reason in {"malformed_text", "missing_product_description", "insufficient_product_detail"}:
        return "text_input_unclear"
    return "text_input_unclear"


def build_product_research_graph(
    extraction_client_factory: ExtractionClientFactory,
    discovery_client_factory: DiscoveryClientFactory,
    ranking_client_factory: RankingClientFactory,
):
    graph = StateGraph(AgentGraphRuntimeState)
    graph.add_node("load_job_context", load_job_context_node)
    graph.add_node("missing_job", missing_job_node)
    graph.add_node("prepare_artifacts", prepare_artifacts_node)
    graph.add_node("screen_text_safety", screen_text_safety_node(extraction_client_factory))
    graph.add_node("fail_unsafe_text", fail_unsafe_text_node)
    graph.add_node("refine_text_input", refine_text_input_node)
    graph.add_node("screen_image_safety", screen_image_safety_node(extraction_client_factory))
    graph.add_node("fail_unsafe_image", fail_unsafe_image_node)
    graph.add_node("refine_ambiguous_image", refine_ambiguous_image_node)
    graph.add_node("understand_image_product", understand_image_product_node(extraction_client_factory))
    graph.add_node("fail_product_understanding", fail_product_understanding_node)
    graph.add_node("refine_product_understanding", refine_product_understanding_node)
    graph.add_node("extract_product_reference", extract_product_reference_node(extraction_client_factory))
    graph.add_node("fail_regulated_product_reference", fail_regulated_product_reference_node)
    graph.add_node("refine_non_product_reference", refine_non_product_reference_node)
    graph.add_node("persist_reference", persist_reference_node)
    graph.add_node("classify_product_profile", classify_product_profile_node(discovery_client_factory))
    graph.add_node("build_search_context", build_search_context_node(discovery_client_factory))
    graph.add_node("plan_search_sources", plan_search_sources_node(discovery_client_factory))
    graph.add_node("execute_search_plan", execute_search_plan_node(discovery_client_factory))
    graph.add_node("normalize_products", normalize_products_node(discovery_client_factory))
    graph.add_node("score_candidates", score_candidates_node(ranking_client_factory))
    graph.add_node("detect_mismatches", detect_mismatches_node(ranking_client_factory))
    graph.add_node("group_candidates", group_candidates_node(ranking_client_factory))
    graph.add_node("explain_ranking", explain_ranking_node(ranking_client_factory))
    graph.add_node("persist_final_brief", persist_final_brief_node)

    graph.add_edge(START, "load_job_context")
    graph.add_conditional_edges(
        "load_job_context",
        route_after_load,
        {
            "missing_job": "missing_job",
            "prepare_artifacts": "prepare_artifacts",
        },
    )
    graph.add_conditional_edges(
        "prepare_artifacts",
        route_by_input_type,
        {
            "screen_text_safety": "screen_text_safety",
            "screen_image_safety": "screen_image_safety",
            "extract_product_reference": "extract_product_reference",
        },
    )
    graph.add_conditional_edges(
        "screen_text_safety",
        route_after_text_safety,
        {
            "fail_unsafe_text": "fail_unsafe_text",
            "refine_text_input": "refine_text_input",
            "screen_image_safety": "screen_image_safety",
            "extract_product_reference": "extract_product_reference",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "screen_image_safety",
        route_after_safety,
        {
            "fail_unsafe_image": "fail_unsafe_image",
            "refine_ambiguous_image": "refine_ambiguous_image",
            "understand_image_product": "understand_image_product",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "understand_image_product",
        route_after_product_understanding,
        {
            "fail_product_understanding": "fail_product_understanding",
            "refine_product_understanding": "refine_product_understanding",
            "fail_regulated_product_reference": "fail_regulated_product_reference",
            "refine_non_product_reference": "refine_non_product_reference",
            "persist_reference": "persist_reference",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "extract_product_reference",
        route_after_reference,
        {
            "fail_regulated_product_reference": "fail_regulated_product_reference",
            "refine_non_product_reference": "refine_non_product_reference",
            "persist_reference": "persist_reference",
            "end": END,
        },
    )
    graph.add_edge("missing_job", END)
    graph.add_edge("fail_unsafe_text", END)
    graph.add_edge("refine_text_input", END)
    graph.add_edge("fail_unsafe_image", END)
    graph.add_edge("refine_ambiguous_image", END)
    graph.add_edge("fail_product_understanding", END)
    graph.add_edge("refine_product_understanding", END)
    graph.add_edge("fail_regulated_product_reference", END)
    graph.add_edge("refine_non_product_reference", END)
    graph.add_edge("persist_reference", "classify_product_profile")
    graph.add_conditional_edges(
        "classify_product_profile",
        route_after_discovery_stage,
        {"continue": "build_search_context", "end": END},
    )
    graph.add_conditional_edges(
        "build_search_context",
        route_after_discovery_stage,
        {"continue": "plan_search_sources", "end": END},
    )
    graph.add_conditional_edges(
        "plan_search_sources",
        route_after_discovery_stage,
        {"continue": "execute_search_plan", "end": END},
    )
    graph.add_conditional_edges(
        "execute_search_plan",
        route_after_discovery_stage,
        {"continue": "normalize_products", "end": END},
    )
    graph.add_conditional_edges(
        "normalize_products",
        route_after_discovery_stage,
        {"continue": "score_candidates", "end": END},
    )
    graph.add_edge("score_candidates", "detect_mismatches")
    graph.add_edge("detect_mismatches", "group_candidates")
    graph.add_edge("group_candidates", "explain_ranking")
    graph.add_edge("explain_ranking", "persist_final_brief")
    graph.add_edge("persist_final_brief", END)
    return graph.compile()
