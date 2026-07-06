import pytest
from sqlalchemy import text

from app.db import engine, run_schema_migrations
from app.job_repository import get_dependency_health, record_dependency_circuit_failure
from app.tool_policy import ToolExecutionPolicy
from app.workflow import safe_provider_message
from app.workflow_contracts import WorkflowProviderError


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def clean_dependency_health() -> None:
    await engine.dispose()
    await run_schema_migrations()
    async with engine.begin() as connection:
        await connection.execute(text("DELETE FROM dependency_health"))
    yield
    await engine.dispose()


class ProviderHTTPError(Exception):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


@pytest.mark.anyio
async def test_postgres_circuit_opens_after_repeated_provider_failures(clean_dependency_health: None) -> None:
    calls = 0

    async def call() -> str:
        nonlocal calls
        calls += 1
        raise ProviderHTTPError("HTTP/1.1 503 Service Unavailable", status_code=503)

    policy = ToolExecutionPolicy(
        timeout_seconds=1,
        max_retries=0,
        circuit_breaker_enabled=True,
        circuit_failure_threshold=2,
        circuit_window_seconds=120,
        circuit_cooldown_seconds=300,
    )

    with pytest.raises(WorkflowProviderError) as first:
        await policy.run(dependency="serpapi", operation="serpapi_research", call=call)

    assert first.value.code == "provider_unavailable"

    with pytest.raises(WorkflowProviderError) as second:
        await policy.run(dependency="serpapi", operation="serpapi_research", call=call)

    assert second.value.code == "provider_unavailable"
    assert calls == 2

    circuit = await get_dependency_health("serpapi_research")
    assert circuit is not None
    assert circuit["state"] == "open"
    assert circuit["recent_failure_count"] == 2
    assert circuit["opened_at"] is not None
    assert circuit["cooldown_until"] is not None

    with pytest.raises(WorkflowProviderError) as third:
        await policy.run(dependency="serpapi", operation="serpapi_research", call=call)

    assert third.value.code == "provider_circuit_open"
    assert calls == 2


@pytest.mark.anyio
async def test_open_circuit_fails_fast_without_invoking_provider(clean_dependency_health: None) -> None:
    await record_dependency_circuit_failure(
        "gemini_extract",
        failure_threshold=1,
        window_seconds=120,
        cooldown_seconds=300,
    )
    calls = 0

    async def call() -> str:
        nonlocal calls
        calls += 1
        return "should not run"

    with pytest.raises(WorkflowProviderError) as exc:
        await ToolExecutionPolicy(
            timeout_seconds=1,
            max_retries=0,
            circuit_breaker_enabled=True,
        ).run(
            dependency="gemini",
            operation="gemini_extract",
            call=call,
        )

    assert exc.value.code == "provider_circuit_open"
    assert exc.value.retryable is True
    assert calls == 0
    assert safe_provider_message(exc.value.code) == "Provider is temporarily unavailable. Try again shortly."


@pytest.mark.anyio
async def test_expired_open_circuit_allows_probe_and_success_closes_circuit(clean_dependency_health: None) -> None:
    await record_dependency_circuit_failure(
        "gemini_extract",
        failure_threshold=1,
        window_seconds=120,
        cooldown_seconds=0,
    )

    async def call() -> str:
        return "ok"

    result = await ToolExecutionPolicy(
        timeout_seconds=1,
        max_retries=0,
        circuit_breaker_enabled=True,
    ).run(
        dependency="gemini",
        operation="gemini_extract",
        call=call,
    )

    circuit = await get_dependency_health("gemini_extract")
    assert result == "ok"
    assert circuit is not None
    assert circuit["state"] == "healthy"
    assert circuit["recent_failure_count"] == 0
    assert circuit["cooldown_until"] is None
