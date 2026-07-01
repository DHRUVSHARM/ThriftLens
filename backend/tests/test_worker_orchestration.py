import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from uuid import uuid4

from app.db import engine, run_schema_migrations
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
from app.workflow import ResearchWorkflow


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


async def _create_image_job(client: AsyncClient) -> str:
    job_id = str(uuid4())
    await create_research_job(
        job_id=job_id,
        provider_mode="SAMPLE_MODE",
        input_type="image",
        request_payload={
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
    assert await count_job_attempts(job_id) >= 4


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
