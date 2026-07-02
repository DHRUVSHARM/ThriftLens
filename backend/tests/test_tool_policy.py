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

    async def fake_get_dependency_health(dependency: str) -> None:
        return None

    async def fake_mark_dependency_circuit_half_open(dependency: str) -> None:
        return None

    async def fake_record_dependency_circuit_success(dependency: str) -> None:
        return None

    async def fake_record_dependency_circuit_failure(
        dependency: str,
        *,
        failure_threshold: int,
        window_seconds: int,
        cooldown_seconds: int,
    ) -> dict[str, object]:
        return {"dependency": dependency, "state": "degraded"}

    monkeypatch.setattr(tool_policy_module, "update_dependency_health", fake_update_dependency_health)
    monkeypatch.setattr(tool_policy_module, "get_dependency_health", fake_get_dependency_health)
    monkeypatch.setattr(tool_policy_module, "mark_dependency_circuit_half_open", fake_mark_dependency_circuit_half_open)
    monkeypatch.setattr(tool_policy_module, "record_dependency_circuit_success", fake_record_dependency_circuit_success)
    monkeypatch.setattr(tool_policy_module, "record_dependency_circuit_failure", fake_record_dependency_circuit_failure)
    return events


class ProviderHTTPError(Exception):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


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
    sleep_delays: list[float] = []

    async def call() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise WorkflowProviderError("temporary_failure", "Temporary failure.", retryable=True)
        return "ok"

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    result = await ToolExecutionPolicy(
        timeout_seconds=1,
        max_retries=1,
        backoff_base_seconds=2,
        jitter_ratio=0,
        sleeper=fake_sleep,
    ).run(
        dependency="gemini",
        operation="extract",
        call=call,
    )

    assert result == "ok"
    assert calls == 2
    assert sleep_delays == [2]
    assert health_events == [
        {"dependency": "gemini", "state": "degraded", "failure": True},
        {"dependency": "gemini", "state": "healthy", "failure": False},
    ]


def test_tool_policy_backoff_uses_exponential_delay_with_jitter() -> None:
    policy = ToolExecutionPolicy(
        timeout_seconds=1,
        max_retries=1,
        backoff_base_seconds=2,
        backoff_max_seconds=15,
        jitter_ratio=0.25,
        random_between=lambda low, high: high,
    )

    assert policy._calculate_backoff_seconds(0) == 2.5
    assert policy._calculate_backoff_seconds(1) == 5.0


@pytest.mark.anyio
async def test_tool_policy_non_retryable_provider_error_does_not_retry(
    health_events: list[dict[str, object]],
) -> None:
    calls = 0

    async def call() -> str:
        nonlocal calls
        calls += 1
        raise WorkflowProviderError("gemini_configuration_missing", "Gemini API key missing.", retryable=False)

    with pytest.raises(WorkflowProviderError) as exc:
        await ToolExecutionPolicy(timeout_seconds=1, max_retries=3).run(
            dependency="gemini",
            operation="extract",
            call=call,
        )

    assert exc.value.code == "provider_configuration_error"
    assert str(exc.value) == "Live provider configuration is incomplete."
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

    assert exc.value.code == "provider_timeout"
    assert str(exc.value) == "Provider request timed out."
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

    assert exc.value.code == "provider_unavailable"
    assert str(exc.value) == "Provider is temporarily unavailable."
    assert "secret-serpapi-key" not in str(exc.value)
    assert health_events == [{"dependency": "serpapi", "state": "degraded", "failure": True}]


@pytest.mark.anyio
async def test_tool_policy_classifies_429_as_retryable_rate_limit(
    health_events: list[dict[str, object]],
) -> None:
    calls = 0
    sleep_delays: list[float] = []

    async def call() -> str:
        nonlocal calls
        calls += 1
        raise ProviderHTTPError("HTTP/1.1 429 Too Many Requests", status_code=429)

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    with pytest.raises(WorkflowProviderError) as exc:
        await ToolExecutionPolicy(
            timeout_seconds=1,
            max_retries=1,
            backoff_base_seconds=2,
            jitter_ratio=0,
            sleeper=fake_sleep,
        ).run(
            dependency="gemini",
            operation="gemini_extract",
            call=call,
        )

    assert exc.value.code == "provider_rate_limited"
    assert exc.value.retryable is True
    assert calls == 2
    assert sleep_delays == [2]
    assert health_events == [
        {"dependency": "gemini", "state": "degraded", "failure": True},
        {"dependency": "gemini", "state": "degraded", "failure": True},
    ]


@pytest.mark.anyio
async def test_tool_policy_provider_max_retries_zero_makes_single_attempt(
    health_events: list[dict[str, object]],
) -> None:
    calls = 0

    async def call() -> str:
        nonlocal calls
        calls += 1
        raise ProviderHTTPError("HTTP/1.1 503 Service Unavailable", status_code=503)

    with pytest.raises(WorkflowProviderError) as exc:
        await ToolExecutionPolicy(timeout_seconds=1, max_retries=0).run(
            dependency="serpapi",
            operation="serpapi_research",
            call=call,
        )

    assert exc.value.code == "provider_unavailable"
    assert calls == 1


@pytest.mark.anyio
async def test_tool_policy_respects_retry_after_hint(
    health_events: list[dict[str, object]],
) -> None:
    calls = 0
    sleep_delays: list[float] = []

    class RateLimitWithRetryAfter(Exception):
        status_code = 429
        headers = {"retry-after": "4"}

    async def call() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RateLimitWithRetryAfter("Too Many Requests")
        return "ok"

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    result = await ToolExecutionPolicy(
        timeout_seconds=1,
        max_retries=1,
        backoff_max_seconds=15,
        sleeper=fake_sleep,
    ).run(
        dependency="gemini",
        operation="gemini_extract",
        call=call,
    )

    assert result == "ok"
    assert sleep_delays == [4]
