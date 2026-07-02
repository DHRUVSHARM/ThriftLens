import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
import random
from typing import TypeVar

from app.config import get_settings
from app.job_repository import (
    get_dependency_health,
    mark_dependency_circuit_half_open,
    record_dependency_circuit_failure,
    record_dependency_circuit_success,
    update_dependency_health,
)
from app.workflow_contracts import WorkflowProviderError

T = TypeVar("T")
Sleeper = Callable[[float], Awaitable[None]]
RandomBetween = Callable[[float, float], float]

RATE_LIMIT_MARKERS = ("429", "too many requests", "rate limit", "rate_limit", "resource_exhausted", "resource exhausted")
QUOTA_MARKERS = ("quota exhausted", "quota exceeded", "daily limit", "insufficient quota")
CONFIGURATION_MARKERS = (
    "401",
    "403",
    "api key",
    "apikey",
    "auth",
    "billing disabled",
    "configuration_missing",
    "credentials",
    "forbidden",
    "invalid key",
    "permission denied",
    "unauthorized",
)
UNAVAILABLE_MARKERS = (
    "500",
    "502",
    "503",
    "504",
    "connection",
    "connection refused",
    "connect timeout",
    "service unavailable",
    "temporarily unavailable",
    "transport",
)


class ToolExecutionPolicy:
    def __init__(
        self,
        *,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        backoff_base_seconds: float | None = None,
        backoff_max_seconds: float | None = None,
        jitter_ratio: float | None = None,
        circuit_breaker_enabled: bool | None = None,
        circuit_failure_threshold: int | None = None,
        circuit_window_seconds: int | None = None,
        circuit_cooldown_seconds: int | None = None,
        sleeper: Sleeper | None = None,
        random_between: RandomBetween | None = None,
    ) -> None:
        settings = get_settings()
        self.timeout_seconds = timeout_seconds or settings.provider_timeout_seconds
        self.max_retries = settings.provider_max_retries if max_retries is None else max_retries
        self.backoff_base_seconds = backoff_base_seconds or settings.provider_backoff_base_seconds
        self.backoff_max_seconds = backoff_max_seconds or settings.provider_backoff_max_seconds
        self.jitter_ratio = settings.provider_jitter_ratio if jitter_ratio is None else jitter_ratio
        self.circuit_breaker_enabled = (
            settings.provider_mode == "REAL_MODE" if circuit_breaker_enabled is None else circuit_breaker_enabled
        )
        self.circuit_failure_threshold = circuit_failure_threshold or settings.circuit_breaker_failure_threshold
        self.circuit_window_seconds = circuit_window_seconds or settings.circuit_breaker_window_seconds
        self.circuit_cooldown_seconds = circuit_cooldown_seconds or settings.circuit_breaker_cooldown_seconds
        self.sleeper = sleeper or asyncio.sleep
        self.random_between = random_between or random.uniform

    async def run(
        self,
        *,
        dependency: str,
        operation: str,
        call: Callable[[], Awaitable[T]],
    ) -> T:
        last_error: WorkflowProviderError | None = None
        await self._raise_if_circuit_open(operation)
        for attempt in range(self.max_retries + 1):
            try:
                result = await asyncio.wait_for(call(), timeout=self.timeout_seconds)
                await update_dependency_health(dependency=dependency, state="healthy")
                await self._record_circuit_success(operation)
                return result
            except WorkflowProviderError as exc:
                last_error = classify_provider_error(exc)
                await update_dependency_health(dependency=dependency, state="degraded", failure=True)
                await self._record_circuit_failure(operation, last_error)
                if not last_error.retryable or attempt >= self.max_retries:
                    raise last_error from exc
                await self._sleep_before_retry(attempt, retry_after_seconds_from(exc))
            except TimeoutError as exc:
                last_error = WorkflowProviderError(
                    "provider_timeout",
                    "Provider request timed out.",
                    retryable=True,
                )
                await update_dependency_health(dependency=dependency, state="degraded", failure=True)
                await self._record_circuit_failure(operation, last_error)
                if attempt >= self.max_retries:
                    raise last_error from exc
                await self._sleep_before_retry(attempt, None)
            except Exception as exc:
                last_error = classify_provider_exception(exc)
                await update_dependency_health(dependency=dependency, state="degraded", failure=True)
                await self._record_circuit_failure(operation, last_error)
                if not last_error.retryable or attempt >= self.max_retries:
                    raise last_error from exc
                await self._sleep_before_retry(attempt, retry_after_seconds_from(exc))

        raise last_error or WorkflowProviderError(
            "provider_unavailable",
            "Provider is temporarily unavailable.",
            retryable=True,
        )

    async def _sleep_before_retry(self, attempt_index: int, retry_after_seconds: float | None) -> None:
        delay = retry_after_seconds
        if delay is None:
            delay = self._calculate_backoff_seconds(attempt_index)
        await self.sleeper(min(delay, self.backoff_max_seconds))

    def _calculate_backoff_seconds(self, attempt_index: int) -> float:
        raw_delay = min(self.backoff_max_seconds, self.backoff_base_seconds * (2**attempt_index))
        jitter = raw_delay * self.jitter_ratio
        if jitter <= 0:
            return raw_delay
        return self.random_between(max(0.0, raw_delay - jitter), raw_delay + jitter)

    async def _raise_if_circuit_open(self, operation: str) -> None:
        if not self.circuit_breaker_enabled:
            return
        circuit = await get_dependency_health(operation)
        if circuit is None or circuit["state"] != "open":
            return

        cooldown_until = circuit.get("cooldown_until")
        now = datetime.now(timezone.utc)
        if cooldown_until is not None and cooldown_until > now:
            raise WorkflowProviderError(
                "provider_circuit_open",
                "Provider circuit is temporarily open.",
                retryable=True,
            )
        await mark_dependency_circuit_half_open(operation)

    async def _record_circuit_success(self, operation: str) -> None:
        if self.circuit_breaker_enabled:
            await record_dependency_circuit_success(operation)

    async def _record_circuit_failure(self, operation: str, error: WorkflowProviderError) -> None:
        if not self.circuit_breaker_enabled or not error.retryable:
            return
        circuit = await record_dependency_circuit_failure(
            operation,
            failure_threshold=self.circuit_failure_threshold,
            window_seconds=self.circuit_window_seconds,
            cooldown_seconds=self.circuit_cooldown_seconds,
        )
        if circuit["state"] == "open":
            raise WorkflowProviderError(
                "provider_circuit_open",
                "Provider circuit is temporarily open.",
                retryable=True,
            )


def classify_provider_error(exc: WorkflowProviderError) -> WorkflowProviderError:
    text = exception_text(exc)
    if has_marker(text, CONFIGURATION_MARKERS):
        return WorkflowProviderError(
            "provider_configuration_error",
            "Live provider configuration is incomplete.",
            retryable=False,
        )
    if has_marker(text, QUOTA_MARKERS):
        return WorkflowProviderError(
            "provider_quota_exhausted",
            "Provider quota is temporarily exhausted.",
            retryable=False,
        )
    if has_marker(text, RATE_LIMIT_MARKERS):
        return WorkflowProviderError(
            "provider_rate_limited",
            "Provider is temporarily rate-limited.",
            retryable=True,
        )
    if exc.code.endswith("_unavailable") or has_marker(text, UNAVAILABLE_MARKERS):
        return WorkflowProviderError(
            "provider_unavailable",
            "Provider is temporarily unavailable.",
            retryable=exc.retryable,
        )
    return exc


def classify_provider_exception(exc: Exception) -> WorkflowProviderError:
    text = exception_text(exc)
    if has_marker(text, CONFIGURATION_MARKERS):
        return WorkflowProviderError(
            "provider_configuration_error",
            "Live provider configuration is incomplete.",
            retryable=False,
        )
    if has_marker(text, QUOTA_MARKERS):
        return WorkflowProviderError(
            "provider_quota_exhausted",
            "Provider quota is temporarily exhausted.",
            retryable=False,
        )
    if has_marker(text, RATE_LIMIT_MARKERS):
        return WorkflowProviderError(
            "provider_rate_limited",
            "Provider is temporarily rate-limited.",
            retryable=True,
        )
    return WorkflowProviderError(
        "provider_unavailable",
        "Provider is temporarily unavailable.",
        retryable=True,
    )


def exception_text(exc: Exception) -> str:
    values = [exc.__class__.__name__, str(exc)]
    for attr in ("code", "status", "status_code", "reason"):
        value = getattr(exc, attr, None)
        if value is not None:
            values.append(str(value))

    response = getattr(exc, "response", None)
    if response is not None:
        for attr in ("status", "status_code", "reason"):
            value = getattr(response, attr, None)
            if value is not None:
                values.append(str(value))

    return " ".join(values).lower()


def has_marker(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def retry_after_seconds_from(exc: Exception) -> float | None:
    for attr in ("retry_after_seconds", "retry_after"):
        value = getattr(exc, attr, None)
        parsed = parse_retry_after(value)
        if parsed is not None:
            return parsed

    for header_source in (getattr(exc, "headers", None), getattr(getattr(exc, "response", None), "headers", None)):
        if not header_source:
            continue
        value = header_source.get("retry-after") or header_source.get("Retry-After")
        parsed = parse_retry_after(value)
        if parsed is not None:
            return parsed

    return None


def parse_retry_after(value: object) -> float | None:
    if isinstance(value, (int, float)) and value >= 0:
        return float(value)
    if isinstance(value, str):
        try:
            parsed = float(value.strip())
        except ValueError:
            return None
        if parsed >= 0:
            return parsed
    return None
