import asyncio

import pytest

import app.tool_policy as tool_policy_module
from app.tool_policy import ToolExecutionPolicy
from app.workflow_contracts import WorkflowProviderError


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def health_events(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []

    async def fake_update_dependency_health(
        *,
        dependency: str,
        state: str,
        failure: bool = False,
    ) -> None:
        events.append({"dependency": dependency, "state": state, "failure": failure})

    monkeypatch.setattr(tool_policy_module, "update_dependency_health", fake_update_dependency_health)
    return events


@pytest.mark.anyio
async def test_tool_policy_success_marks_dependency_healthy(health_events: list[dict[str, object]]) -> None:
    async def call() -> str:
        return "ok"

    result = await ToolExecutionPolicy(timeout_seconds=1, max_retries=0).run(
        dependency="serpapi",
        operation="search",
        call=call,
    )

    assert result == "ok"
    assert health_events == [{"dependency": "serpapi", "state": "healthy", "failure": False}]


@pytest.mark.anyio
async def test_tool_policy_retries_retryable_provider_error_then_succeeds(
    health_events: list[dict[str, object]],
) -> None:
    calls = 0

    async def call() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise WorkflowProviderError("temporary_failure", "Temporary failure.", retryable=True)
        return "ok"

    result = await ToolExecutionPolicy(timeout_seconds=1, max_retries=1).run(
        dependency="gemini",
        operation="extract",
        call=call,
    )

    assert result == "ok"
    assert calls == 2
    assert health_events == [
        {"dependency": "gemini", "state": "degraded", "failure": True},
        {"dependency": "gemini", "state": "healthy", "failure": False},
    ]


@pytest.mark.anyio
async def test_tool_policy_non_retryable_provider_error_does_not_retry(
    health_events: list[dict[str, object]],
) -> None:
    calls = 0

    async def call() -> str:
        nonlocal calls
        calls += 1
        raise WorkflowProviderError("configuration_missing", "Provider key missing.", retryable=False)

    with pytest.raises(WorkflowProviderError) as exc:
        await ToolExecutionPolicy(timeout_seconds=1, max_retries=3).run(
            dependency="gemini",
            operation="extract",
            call=call,
        )

    assert exc.value.code == "configuration_missing"
    assert calls == 1
    assert health_events == [{"dependency": "gemini", "state": "degraded", "failure": True}]


@pytest.mark.anyio
async def test_tool_policy_timeout_becomes_structured_retryable_error(
    health_events: list[dict[str, object]],
) -> None:
    async def call() -> str:
        await asyncio.sleep(1)
        return "too late"

    with pytest.raises(WorkflowProviderError) as exc:
        await ToolExecutionPolicy(timeout_seconds=0.001, max_retries=0).run(
            dependency="serpapi",
            operation="search",
            call=call,
        )

    assert exc.value.code == "search_timeout"
    assert str(exc.value) == "search timed out."
    assert exc.value.retryable is True
    assert health_events == [{"dependency": "serpapi", "state": "degraded", "failure": True}]


@pytest.mark.anyio
async def test_tool_policy_generic_exception_becomes_safe_unavailable_error(
    health_events: list[dict[str, object]],
) -> None:
    async def call() -> str:
        raise RuntimeError("raw provider failure with secret-serpapi-key")

    with pytest.raises(WorkflowProviderError) as exc:
        await ToolExecutionPolicy(timeout_seconds=1, max_retries=0).run(
            dependency="serpapi",
            operation="search",
            call=call,
        )

    assert exc.value.code == "search_unavailable"
    assert str(exc.value) == "search is temporarily unavailable."
    assert "secret-serpapi-key" not in str(exc.value)
    assert health_events == [{"dependency": "serpapi", "state": "degraded", "failure": True}]
