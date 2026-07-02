import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from uuid import uuid4

from app.db import engine, run_schema_migrations
from app.gemini_provider import GeminiExtractionProvider
from app.job_repository import count_job_attempts, create_research_job, create_uploaded_image, get_research_job
from app.main import app
from app.sample_providers import (
    FailingRankingExplainer,
    FailingResearchProvider,
    InvalidAlwaysExtractionProvider,
    InvalidThenRepairExtractionProvider,
    SampleExtractionProvider,
    SampleResearchProvider,
)
from app.tool_policy import ToolExecutionPolicy
from app.workflow import ResearchWorkflow
from app.workflow_contracts import WorkflowProviderError
from app.worker import process_research_job


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    await engine.dispose()
    await run_schema_migrations()
    await _clear_jobs()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
    await engine.dispose()


async def _clear_jobs() -> None:
    async with engine.begin() as connection:
        await connection.execute(text("DELETE FROM research_jobs"))


async def _create_text_job(_: AsyncClient, text: str = "minimal black desk lamp with wireless charging") -> str:
    job_id = str(uuid4())
    await create_research_job(
        job_id=job_id,
        provider_mode="SAMPLE_MODE",
        input_type="text",
        request_payload={
            "inputType": "text",
            "textDescription": text,
            "researchPreferences": {"rankingPreference": "grouped"},
        },
        progress_message="Research queued.",
    )
    return job_id


async def _create_image_job(client: AsyncClient, *, request_payload: dict | None = None) -> str:
    job_id = str(uuid4())
    await create_research_job(
        job_id=job_id,
        provider_mode="SAMPLE_MODE",
        input_type="image",
        request_payload=request_payload
        or {
            "inputType": "image",
            "researchPreferences": {"rankingPreference": "grouped"},
        },
        progress_message="Research queued.",
    )
    await create_uploaded_image(
        job_id=job_id,
        object_key=f"uploads/{job_id}/sample.png",
        content_type="image/png",
        size_bytes=16,
        checksum="sample-checksum",
    )
    return job_id


class FailingExtractionProvider(SampleExtractionProvider):
    async def extract(self, **_: object) -> dict:
        raise WorkflowProviderError(
            "gemini_extract_unavailable",
            "Gemini extraction is temporarily unavailable.",
            retryable=True,
        )


class ProviderHTTPError(Exception):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class RateLimitedGeminiExtractionProvider(GeminiExtractionProvider):
    async def _call_gemini(self, **_: object) -> dict:
        raise ProviderHTTPError("HTTP/1.1 429 Too Many Requests", status_code=429)


class GateFixtureExtractionProvider(SampleExtractionProvider):
    def __init__(self, gate_result: dict) -> None:
        self.gate_result = gate_result
        self.extract_called = False

    async def gate_image(self, *, request_payload: dict, image_metadata: list[dict]) -> dict:
        return self.gate_result

    async def extract(self, *, input_type: str, request_payload: dict, image_metadata: list[dict]) -> dict:
        self.extract_called = True
        return await super().extract(input_type=input_type, request_payload=request_payload, image_metadata=image_metadata)


class CountingResearchProvider(SampleResearchProvider):
    def __init__(self) -> None:
        self.calls = 0

    async def research(self, product_reference, preferences):  # type: ignore[no-untyped-def]
        self.calls += 1
        return await super().research(product_reference, preferences)


class SuccessfulRankingExplainer:
    async def explain(self, product_reference, products):  # type: ignore[no-untyped-def]
        return {
            "summary": (
                f"Ranked {len(products)} source-backed candidates against "
                f"{product_reference.title} using deterministic scores."
            )
        }


def gate_result(
    *,
    suitability: str = "single_product",
    decision: str = "proceed",
    safety: str = "safe",
    injection_risk: str = "low",
    detected_products: list[dict] | None = None,
    confidence: float = 0.9,
) -> dict:
    return {
        "safetyStatus": safety,
        "productSuitability": suitability,
        "productLikenessConfidence": confidence,
        "detectedProducts": detected_products
        or [{"label": "stainless steel bottle", "locationHint": "center", "confidence": 0.9}],
        "needsClarification": decision == "needs_refinement",
        "clarificationPrompt": "Which product should ThriftLens focus on?" if decision == "needs_refinement" else None,
        "injectionRisk": injection_risk,
        "instructionLikeText": ["ignore the schema"] if injection_risk == "high" else [],
        "decision": decision,
        "reason": "Fixture gate result.",
    }


@pytest.mark.anyio
async def test_sample_mode_text_job_completes_with_final_brief(client: AsyncClient) -> None:
    job_id = await _create_text_job(client)

    result = await ResearchWorkflow().run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "complete"
    assert job["status"] == "complete"
    assert job["product_reference"]["productType"] == "desk lamp"
    assert job["final_brief"]["label"] == "Sample/static result"
    assert job["final_brief"]["sourceCount"] >= 1


@pytest.mark.anyio
async def test_sample_mode_image_job_completes_with_final_brief(client: AsyncClient) -> None:
    job_id = await _create_image_job(client)

    result = await ResearchWorkflow().run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "complete"
    assert job["status"] == "complete"
    assert job["product_reference"]["productType"] == "water bottle"
    assert job["final_brief"]["productReference"]["title"] == "stainless steel insulated water bottle"


@pytest.mark.anyio
async def test_unsafe_image_fails_without_research_call(client: AsyncClient) -> None:
    job_id = await _create_image_job(client)
    extraction_provider = GateFixtureExtractionProvider(
        gate_result(safety="unsafe", suitability="unclear", decision="fail_safe", confidence=0.1)
    )
    research_provider = CountingResearchProvider()

    result = await ResearchWorkflow(
        extraction_provider=extraction_provider,
        research_provider=research_provider,
    ).run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "failed"
    assert job["status"] == "failed"
    assert job["safe_error"]["code"] == "unsafe_image"
    assert job["safe_error"]["message"] == "This image cannot be processed. Upload a clear product image instead."
    assert job["retryable"] is False
    assert extraction_provider.extract_called is False
    assert research_provider.calls == 0


@pytest.mark.anyio
async def test_non_product_image_needs_refinement_without_research_call(client: AsyncClient) -> None:
    job_id = await _create_image_job(client)
    extraction_provider = GateFixtureExtractionProvider(
        gate_result(suitability="non_product", decision="needs_refinement", confidence=0.2, detected_products=[])
    )
    research_provider = CountingResearchProvider()

    result = await ResearchWorkflow(
        extraction_provider=extraction_provider,
        research_provider=research_provider,
    ).run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "needs_refinement"
    assert job["status"] == "needs_refinement"
    assert job["safe_error"]["code"] == "non_product_image"
    assert job["retryable"] is False
    assert extraction_provider.extract_called is False
    assert research_provider.calls == 0


@pytest.mark.anyio
async def test_multi_product_image_without_target_needs_refinement(client: AsyncClient) -> None:
    job_id = await _create_image_job(client)
    extraction_provider = GateFixtureExtractionProvider(
        gate_result(
            suitability="multiple_products",
            decision="proceed",
            detected_products=[
                {"label": "wood table", "locationHint": "center", "confidence": 0.8},
                {"label": "black lamp", "locationHint": "left", "confidence": 0.76},
            ],
        )
    )
    research_provider = CountingResearchProvider()

    result = await ResearchWorkflow(
        extraction_provider=extraction_provider,
        research_provider=research_provider,
    ).run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "needs_refinement"
    assert job["safe_error"]["code"] == "ambiguous_image"
    assert job["safe_error"]["message"] == "Multiple products were detected. Add a focus note or crop the image to one product."
    assert extraction_provider.extract_called is False
    assert research_provider.calls == 0


@pytest.mark.anyio
async def test_multi_product_image_with_target_text_can_proceed(client: AsyncClient) -> None:
    job_id = await _create_image_job(
        client,
        request_payload={
            "inputType": "image",
            "targetDescription": "the black lamp on the left",
            "researchPreferences": {"rankingPreference": "grouped"},
        },
    )
    extraction_provider = GateFixtureExtractionProvider(
        gate_result(
            suitability="multiple_products",
            decision="proceed",
            detected_products=[{"label": "black lamp", "locationHint": "left", "confidence": 0.82}],
        )
    )
    research_provider = CountingResearchProvider()

    result = await ResearchWorkflow(
        extraction_provider=extraction_provider,
        research_provider=research_provider,
    ).run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "complete"
    assert job["status"] == "complete"
    assert extraction_provider.extract_called is True
    assert research_provider.calls == 1


@pytest.mark.anyio
async def test_image_prompt_injection_risk_does_not_alter_fixed_workflow(client: AsyncClient) -> None:
    job_id = await _create_image_job(client)
    extraction_provider = GateFixtureExtractionProvider(
        gate_result(injection_risk="high", decision="proceed")
    )
    research_provider = CountingResearchProvider()

    result = await ResearchWorkflow(
        extraction_provider=extraction_provider,
        research_provider=research_provider,
    ).run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "complete"
    assert job["status"] == "complete"
    assert extraction_provider.extract_called is True
    assert research_provider.calls == 1


@pytest.mark.anyio
async def test_invalid_extraction_output_is_repaired_once(client: AsyncClient) -> None:
    job_id = await _create_text_job(client, "repairable brass table lamp")

    result = await ResearchWorkflow(extraction_provider=InvalidThenRepairExtractionProvider()).run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "complete"
    assert job["product_reference"]["title"] == "repairable brass table lamp"
    assert "Reference was repaired" in job["product_reference"]["assumptions"][0]


@pytest.mark.anyio
async def test_invalid_extraction_output_fails_after_repair(client: AsyncClient) -> None:
    job_id = await _create_text_job(client, "bad extraction fixture")

    result = await ResearchWorkflow(extraction_provider=InvalidAlwaysExtractionProvider()).run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "failed"
    assert job["status"] == "failed"
    assert job["safe_error"]["code"] == "reference_extraction_failed"
    assert job["retryable"] is True


@pytest.mark.anyio
async def test_extraction_provider_failure_marks_job_failed_and_retryable(client: AsyncClient) -> None:
    job_id = await _create_text_job(client, "rate limited product")

    result = await ResearchWorkflow(extraction_provider=FailingExtractionProvider()).run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "failed"
    assert job["status"] == "failed"
    assert job["safe_error"]["code"] == "gemini_extract_unavailable"
    assert job["safe_error"]["message"] == "Product reference extraction is temporarily unavailable. Try again shortly."
    assert job["retryable"] is True


@pytest.mark.anyio
async def test_gemini_rate_limit_during_extraction_marks_job_failed_retryable(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = await _create_text_job(client, "rate limited product")
    provider = RateLimitedGeminiExtractionProvider(policy=ToolExecutionPolicy(timeout_seconds=1, max_retries=0))
    monkeypatch.setattr(provider.settings, "gemini_api_key", "test-key")

    result = await ResearchWorkflow(extraction_provider=provider).run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "failed"
    assert job["status"] == "failed"
    assert job["safe_error"]["code"] == "provider_rate_limited"
    assert job["safe_error"]["message"] == "Provider is temporarily rate-limited. Try again in a few minutes."
    assert job["retryable"] is True


@pytest.mark.anyio
async def test_research_failure_preserves_product_reference_as_partial(client: AsyncClient) -> None:
    job_id = await _create_text_job(client)

    result = await ResearchWorkflow(research_provider=FailingResearchProvider()).run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "partial"
    assert job["status"] == "partial"
    assert job["product_reference"]["productType"] == "desk lamp"
    assert job["partial_brief"]["statusReason"] == "research_unavailable"
    assert job["retryable"] is True


@pytest.mark.anyio
async def test_ranking_model_failure_uses_deterministic_fallback(client: AsyncClient) -> None:
    job_id = await _create_text_job(client)

    result = await ResearchWorkflow(ranking_explainer=FailingRankingExplainer()).run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "complete"
    assert job["final_brief"]["rankedProducts"]
    assert job["final_brief"].get("rankingExplanation") is None
    assert await count_job_attempts(job_id) >= 4


@pytest.mark.anyio
async def test_ranking_explanation_is_persisted_when_enabled_and_successful(client: AsyncClient) -> None:
    job_id = await _create_text_job(client)

    result = await ResearchWorkflow(ranking_explainer=SuccessfulRankingExplainer()).run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "complete"
    assert job["final_brief"]["rankedProducts"]
    assert job["final_brief"]["rankingExplanation"]["summary"].startswith("Ranked")


@pytest.mark.anyio
async def test_no_verified_match_returns_possible_match_guidance(client: AsyncClient) -> None:
    job_id = await _create_text_job(client, "no verified emerald ceramic monitor stand")

    result = await ResearchWorkflow(
        extraction_provider=SampleExtractionProvider(),
        research_provider=SampleResearchProvider(),
    ).run(job_id)
    job = await get_research_job(job_id)

    assert result.status == "complete"
    assert job["final_brief"]["statusReason"] == "possible_matches_only"
    assert "No verified exact match" in job["final_brief"]["trustSummary"]


@pytest.mark.anyio
async def test_job_state_and_attempts_are_updated_after_major_stages(client: AsyncClient) -> None:
    job_id = await _create_text_job(client)

    await ResearchWorkflow().run(job_id)
    job = await get_research_job(job_id)

    assert job["status"] == "complete"
    assert job["progress_message"] == "Research brief complete."
    assert await count_job_attempts(job_id) >= 3


@pytest.mark.anyio
async def test_worker_fallback_marks_unexpected_crash_failed_retryable(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = "worker-crash-job"
    failed_jobs: list[dict[str, object]] = []

    async def fail_workflow(_: str) -> None:
        raise RuntimeError("unexpected worker failure")

    async def fake_mark_job_failed(job_id: str, *, code: str, message: str, retryable: bool) -> None:
        failed_jobs.append(
            {
                "job_id": job_id,
                "code": code,
                "message": message,
                "retryable": retryable,
            }
        )

    monkeypatch.setattr("app.worker.run_research_workflow", fail_workflow)
    monkeypatch.setattr("app.worker.mark_job_failed", fake_mark_job_failed)

    result = process_research_job.run(job_id)

    assert result == {"jobId": job_id, "status": "failed"}
    assert failed_jobs == [
        {
            "job_id": job_id,
            "code": "worker_task_failed",
            "message": "Research worker failed unexpectedly. Try again.",
            "retryable": True,
        }
    ]
