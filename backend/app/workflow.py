from typing import Any

from pydantic import ValidationError

from app.config import get_settings
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
from app.ranking import deterministic_rank
from app.sample_providers import SampleExtractionProvider, SampleResearchProvider
from app.workflow_contracts import (
    ExtractionOutputError,
    ImageGateResult,
    ProductReference,
    ProductResearchBrief,
    SourceProduct,
    WorkflowProviderError,
    WorkflowResult,
    model_dump_alias,
)

PROVIDER_FAILURE_MESSAGES = {
    "provider_rate_limited": "Provider is temporarily rate-limited. Try again in a few minutes.",
    "provider_quota_exhausted": "Provider quota is temporarily exhausted. Try again later or use sample mode.",
    "provider_timeout": "Provider request timed out. Try again shortly.",
    "provider_configuration_error": "Live provider configuration is incomplete.",
    "provider_unavailable": "Provider is temporarily unavailable. Try again shortly.",
    "provider_circuit_open": "Provider is temporarily unavailable. Try again shortly.",
}
INPUT_GATE_MESSAGES = {
    "unsafe_image": "This image cannot be processed. Upload a clear product image instead.",
    "unsafe_text": "This text cannot be processed for product research. Please provide a clear, appropriate product-only description.",
    "regulated_product": "This product category cannot be researched in ThriftLens. Please choose a standard consumer product.",
    "image_safety_unclear": "Please provide an image that clearly shows the product you would like to research.",
    "non_product_image": "This does not look like a product image. Upload a clearer image or describe the product in text.",
    "ambiguous_image": "Multiple products or objects were detected. Add a short focus note, such as the item type, color, or location, or crop the image to one product.",
    "image_instruction_risk": "This image contains instruction-like text. Add a clearer product image or focus note.",
    "text_prompt_injection": "Please describe only the product you want researched. Remove instructions, links, or requests unrelated to the product.",
    "text_input_unclear": "Add a specific product description, such as product type, color, brand, material, or the item to focus on.",
    "text_not_product": "Describe the product you want researched instead of asking for links, websites, or assistant instructions.",
}


class ResearchWorkflow:
    def __init__(
        self,
        *,
        extraction_provider: SampleExtractionProvider | None = None,
        research_provider: SampleResearchProvider | None = None,
        ranking_explainer: Any | None = None,
    ) -> None:
        self.settings = get_settings()
        self.extraction_provider = extraction_provider or SampleExtractionProvider()
        self.research_provider = research_provider or SampleResearchProvider()
        self.ranking_explainer = ranking_explainer

    async def run(self, job_id: str) -> WorkflowResult:
        job = await get_research_job(job_id)
        if job is None:
            return WorkflowResult(jobId=job_id, status="missing")

        request_payload = job["request_payload"] or {}
        preferences = request_payload.get("researchPreferences") or {}
        image_metadata = await get_uploaded_images(job_id)

        if job.get("product_reference"):
            reference = ProductReference.model_validate(job["product_reference"])
        else:
            await update_job_stage(job_id, status="extracting_reference", progress_message="Extracting product reference.")
            await record_job_attempt(job_id=job_id, stage="extractReference", dependency="sample-extraction", attempt=1)

            try:
                if job["input_type"] == "image":
                    await record_job_attempt(job_id=job_id, stage="gateImage", dependency="image-gate", attempt=1)
                    gate = await self._gate_image(request_payload, image_metadata)
                    gate_decision = input_gate_decision(gate, request_payload, self.settings)
                    gate_code = input_gate_code(gate)
                    if gate_decision == "fail_safe":
                        await mark_job_failed(
                            job_id,
                            code=gate_code,
                            message=safe_input_gate_message(gate_code),
                            retryable=False,
                        )
                        return WorkflowResult(jobId=job_id, status="failed")
                    if gate_decision == "needs_refinement":
                        await mark_job_needs_refinement(
                            job_id,
                            code=gate_code,
                            message=safe_input_gate_message(gate_code),
                        )
                        return WorkflowResult(jobId=job_id, status="needs_refinement")
                    quality_reason = image_quality_extraction_reason(gate, request_payload, self.settings)
                    if quality_reason:
                        request_payload = {
                            **request_payload,
                            "_useQualityExtractionModel": True,
                            "_qualityExtractionReason": quality_reason,
                        }

                reference = await self._extract_reference(job["input_type"], request_payload, image_metadata)
            except ExtractionOutputError:
                await mark_job_failed(
                    job_id,
                    code="reference_extraction_failed",
                    message="We could not extract enough product detail. Try a clearer image or more specific description.",
                    retryable=True,
                )
                return WorkflowResult(jobId=job_id, status="failed")
            except WorkflowProviderError as exc:
                await record_job_attempt(
                    job_id=job_id,
                    stage="extractReference",
                    dependency="extraction-provider",
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
                return WorkflowResult(jobId=job_id, status="failed")

            reference_payload = model_dump_alias(reference)
            await store_product_reference(
                job_id,
                product_reference=reference_payload,
                progress_message="Product reference extracted.",
            )
            await update_dependency_health(dependency="sample-extraction", state="healthy")

        await update_job_stage(job_id, status="researching_sources", progress_message="Researching source-backed products.")
        await record_job_attempt(job_id=job_id, stage="researchProducts", dependency="sample-research", attempt=1)
        try:
            raw_products = await self.research_provider.research(reference, preferences)
        except WorkflowProviderError as exc:
            await update_dependency_health(dependency="sample-research", state="degraded", failure=True)
            partial = self._build_research_unavailable_brief(reference, exc.code)
            await store_partial_brief(
                job_id,
                partial_brief=model_dump_alias(partial),
                status="partial",
                progress_message="Product reference extracted, but research sources are unavailable.",
                retryable=exc.retryable,
            )
            return WorkflowResult(jobId=job_id, status="partial")

        source_products = [SourceProduct.model_validate(product) for product in raw_products]
        await update_dependency_health(dependency="sample-research", state="healthy")

        await update_job_stage(job_id, status="ranking_results", progress_message="Ranking source-backed candidates.")
        await record_job_attempt(job_id=job_id, stage="rankProducts", dependency="deterministic-ranking", attempt=1)
        ranked = deterministic_rank(reference, source_products)
        ranking_explanation: dict[str, str] | None = None
        if self.ranking_explainer is not None:
            try:
                ranking_explanation = await self.ranking_explainer.explain(reference, source_products)
            except WorkflowProviderError as exc:
                await record_job_attempt(
                    job_id=job_id,
                    stage="rankProducts",
                    dependency="ranking-model",
                    attempt=1,
                    error_code=exc.code,
                    retryable=exc.retryable,
                )

        brief = self._build_final_brief(reference, ranked, ranking_explanation=ranking_explanation)
        final_job = await store_final_brief(
            job_id,
            final_brief=model_dump_alias(brief),
            status="complete",
            progress_message="Research brief complete.",
        )
        return WorkflowResult(jobId=job_id, status=final_job["status"] if final_job else "complete")

    async def _gate_image(
        self,
        request_payload: dict[str, Any],
        image_metadata: list[dict[str, Any]],
    ) -> ImageGateResult:
        raw = await self.extraction_provider.gate_image(
            request_payload=request_payload,
            image_metadata=image_metadata,
        )
        try:
            return ImageGateResult.model_validate(raw)
        except ValidationError as exc:
            raise ExtractionOutputError("Invalid image gate output.") from exc

    async def _extract_reference(
        self,
        input_type: str,
        request_payload: dict[str, Any],
        image_metadata: list[dict[str, Any]],
    ) -> ProductReference:
        raw = await self.extraction_provider.extract(
            input_type=input_type,
            request_payload=request_payload,
            image_metadata=image_metadata,
        )
        try:
            return ProductReference.model_validate(raw)
        except ValidationError:
            repaired = await self.extraction_provider.repair(raw)
            try:
                return ProductReference.model_validate(repaired)
            except ValidationError as exc:
                raise ExtractionOutputError("Invalid product reference after repair.") from exc

    def _build_research_unavailable_brief(self, reference: ProductReference, code: str) -> ProductResearchBrief:
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
        self,
        reference: ProductReference,
        ranked_products: list,
        *,
        ranking_explanation: dict[str, str] | None = None,
    ) -> ProductResearchBrief:
        has_verified = any(product.group == "closest" and product.score >= 0.74 for product in ranked_products)
        notes = ["Sample/static data, not live market research."]
        if not has_verified:
            notes.append("No verified exact match was found; showing possible alternatives instead.")

        return ProductResearchBrief(
            mode="sample",
            label="Sample/static result",
            productReference=reference,
            trustSummary=(
                "Found a source-backed sample match set."
                if has_verified
                else "No verified exact match was found in the source-backed sample set."
            ),
            sourceCount=len(ranked_products),
            freshnessNote="All source data is deterministic sample/static data.",
            uncertaintyNotes=notes,
            rankedProducts=ranked_products,
            rankingExplanation=ranking_explanation,
            userActions=["Review matches", "Refine description", "Retry with live providers when configured"],
            statusReason=None if has_verified else "possible_matches_only",
        )


async def run_research_workflow(job_id: str) -> WorkflowResult:
    from app.provider_factory import build_research_workflow

    return await build_research_workflow().run(job_id)


def safe_provider_message(code: str) -> str:
    return PROVIDER_FAILURE_MESSAGES.get(code, "Product reference extraction is temporarily unavailable. Try again shortly.")


def safe_input_gate_message(code: str) -> str:
    return INPUT_GATE_MESSAGES.get(code, INPUT_GATE_MESSAGES["ambiguous_image"])


def input_gate_decision(gate: ImageGateResult, request_payload: dict[str, Any], settings: Any) -> str:
    target_description = (request_payload.get("targetDescription") or "").strip()
    best_candidate_confidence = max((product.confidence for product in gate.detected_products), default=0.0)
    too_many_candidates = len(gate.detected_products) > settings.input_gate_max_products_without_target

    if gate.safety_status == "unsafe":
        return "fail_safe"
    if gate.product_suitability == "non_product":
        return "needs_refinement"
    if (
        gate.product_suitability == "unclear"
        and gate.product_likeness_confidence < settings.input_gate_min_product_confidence
    ):
        return "needs_refinement"
    if gate.product_suitability == "multiple_products" and not target_description:
        return "needs_refinement"
    if too_many_candidates and not target_description:
        return "needs_refinement"
    if (
        gate.product_suitability == "multiple_products"
        and best_candidate_confidence < settings.input_gate_target_match_confidence
    ):
        return "needs_refinement"
    if too_many_candidates and best_candidate_confidence < settings.input_gate_target_match_confidence:
        return "needs_refinement"
    return gate.decision


def input_gate_code(gate: ImageGateResult) -> str:
    if gate.safety_status == "unsafe":
        return "unsafe_image"
    if gate.product_suitability == "non_product":
        return "non_product_image"
    if gate.injection_risk == "high" and gate.decision != "proceed":
        return "image_instruction_risk"
    if gate.product_suitability in {"multiple_products", "unclear"}:
        return "ambiguous_image"
    return "ambiguous_image"


def image_quality_extraction_reason(gate: ImageGateResult, request_payload: dict[str, Any], settings: Any) -> str | None:
    target_description = (request_payload.get("targetDescription") or "").strip()
    too_many_candidates = len(gate.detected_products) > settings.input_gate_max_products_without_target
    if (gate.product_suitability == "multiple_products" or too_many_candidates) and target_description:
        return "targeted_multi_product_image"
    if gate.product_likeness_confidence < settings.input_gate_quality_model_confidence:
        return "low_gate_confidence"
    return None
