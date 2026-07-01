import pytest
from anyio import sleep as anyio_sleep
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.config import Settings
from app.db import engine, run_schema_migrations
from app.gateway import assert_real_mode_configured
from app.main import app


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


@pytest.mark.anyio
async def test_create_text_job_returns_queued_and_can_be_polled(client: AsyncClient) -> None:
    response = await client.post(
        "/api/research-jobs",
        json={
            "inputType": "text",
            "textDescription": "minimal black desk lamp with wireless charging",
            "researchPreferences": {"rankingPreference": "grouped"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["jobId"]
    assert body["status"] == "queued"
    assert body["providerMode"] == "SAMPLE_MODE"
    assert body["safeError"] is None

    poll_response = await client.get(f"/api/research-jobs/{body['jobId']}")
    assert poll_response.status_code == 200
    poll_body = poll_response.json()
    assert poll_body["jobId"] == body["jobId"]
    assert "finalBrief" in poll_body


@pytest.mark.anyio
async def test_sample_mode_job_eventually_gets_static_final_brief(client: AsyncClient) -> None:
    response = await client.post(
        "/api/research-jobs",
        json={
            "inputType": "text",
            "textDescription": "stainless steel insulated water bottle",
        },
    )
    assert response.status_code == 200
    job_id = response.json()["jobId"]

    final_body = None
    for _ in range(20):
        poll_body = (await client.get(f"/api/research-jobs/{job_id}")).json()
        if poll_body["status"] == "completed":
            final_body = poll_body
            break
        await anyio_sleep(0.25)

    assert final_body is not None
    assert final_body["finalBrief"]["label"] == "Sample/static result"
    assert final_body["finalBrief"]["sourceNote"] == "No live provider was called in SAMPLE_MODE."


@pytest.mark.anyio
async def test_empty_text_input_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/research-jobs",
        json={"inputType": "text", "textDescription": "   "},
    )

    assert response.status_code == 422
    assert "textDescription is required" in response.text


@pytest.mark.anyio
async def test_unsupported_image_type_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/research-jobs",
        data={"inputType": "image"},
        files={"image": ("note.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 422
    assert "Unsupported image type" in response.text


@pytest.mark.anyio
async def test_oversized_image_is_rejected(client: AsyncClient) -> None:
    oversized = b"x" * (9 * 1024 * 1024)
    response = await client.post(
        "/api/research-jobs",
        data={"inputType": "image"},
        files={"image": ("large.png", oversized, "image/png")},
    )

    assert response.status_code == 413
    assert "8MB or smaller" in response.text


async def _uploaded_image_count(job_id: str) -> int:
    async with engine.connect() as connection:
        result = await connection.execute(
            text("SELECT COUNT(*) FROM uploaded_images WHERE job_id = :job_id"),
            {"job_id": job_id},
        )
        return int(result.scalar_one())


async def _clear_jobs() -> None:
    async with engine.begin() as connection:
        await connection.execute(text("DELETE FROM research_jobs"))


@pytest.mark.anyio
async def test_create_image_job_stores_metadata_and_can_be_polled(client: AsyncClient) -> None:
    response = await client.post(
        "/api/research-jobs",
        data={"inputType": "image"},
        files={"image": ("lamp.png", b"\x89PNG\r\n\x1a\nsample", "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert await _uploaded_image_count(body["jobId"]) == 1

    poll_response = await client.get(f"/api/research-jobs/{body['jobId']}")
    assert poll_response.status_code == 200
    assert poll_response.json()["safeError"] is None


@pytest.mark.anyio
async def test_retry_refuses_non_retryable_job(client: AsyncClient) -> None:
    response = await client.post(
        "/api/research-jobs",
        json={"inputType": "text", "textDescription": "small walnut side table"},
    )
    assert response.status_code == 200

    retry_response = await client.post(f"/api/research-jobs/{response.json()['jobId']}/retry")
    assert retry_response.status_code == 409
    assert retry_response.json()["detail"]["code"] == "job_not_retryable"


def test_real_mode_missing_provider_keys_is_explicit() -> None:
    settings = Settings(
        provider_mode="REAL_MODE",
        gemini_api_key="",
        serpapi_api_key="",
    )

    with pytest.raises(HTTPException) as exc_info:
        assert_real_mode_configured(settings)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "provider_configuration_missing"
    assert exc_info.value.detail["missing"] == ["GEMINI_API_KEY", "SERPAPI_API_KEY"]
