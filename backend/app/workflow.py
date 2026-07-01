from typing import Any

from pydantic import ValidationError

from app.job_repository import (
    get_research_job,
    get_uploaded_images,
    mark_job_failed,
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
    ProductReference,
    ProductResearchBrief,
    SourceProduct,
    WorkflowProviderError,
    WorkflowResult,
    model_dump_alias,
)


class ResearchWorkflow:
    def __init__(
        self,
        *,
        extraction_provider: SampleExtractionProvider | None = None,
        research_provider: SampleResearchProvider | None = None,
        ranking_explainer: Any | None = None,
    ) -> None:
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

        await update_job_stage(job_id, status="extracting_reference", progress_message="Extracting product reference.")
        await record_job_attempt(job_id=job_id, stage="extractReference", dependency="sample-extraction", attempt=1)

        try:
            reference = await self._extract_reference(job["input_type"], request_payload, image_metadata)
        except ExtractionOutputError:
            await mark_job_failed(
                job_id,
                code="reference_extraction_failed",
                message="We could not extract enough product detail. Try a clearer image or more specific description.",
                retryable=True,
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
        if self.ranking_explainer is not None:
            try:
                await self.ranking_explainer.explain(reference, source_products)
            except WorkflowProviderError:
                await record_job_attempt(
                    job_id=job_id,
                    stage="rankProducts",
                    dependency="ranking-model",
                    attempt=1,
                    error_code="ranking_model_unavailable",
                    retryable=True,
                )

        brief = self._build_final_brief(reference, ranked)
        final_job = await store_final_brief(
            job_id,
            final_brief=model_dump_alias(brief),
            status="complete",
            progress_message="Research brief complete.",
        )
        return WorkflowResult(jobId=job_id, status=final_job["status"] if final_job else "complete")

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

    def _build_final_brief(self, reference: ProductReference, ranked_products: list) -> ProductResearchBrief:
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
            userActions=["Review matches", "Refine description", "Retry with live providers when configured"],
            statusReason=None if has_verified else "possible_matches_only",
        )


async def run_research_workflow(job_id: str) -> WorkflowResult:
    from app.provider_factory import build_research_workflow

    return await build_research_workflow().run(job_id)
