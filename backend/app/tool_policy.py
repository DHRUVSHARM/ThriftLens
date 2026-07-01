import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.config import get_settings
from app.job_repository import update_dependency_health
from app.workflow_contracts import WorkflowProviderError

T = TypeVar("T")


class ToolExecutionPolicy:
    def __init__(self, *, timeout_seconds: float | None = None, max_retries: int | None = None) -> None:
        settings = get_settings()
        self.timeout_seconds = timeout_seconds or settings.provider_timeout_seconds
        self.max_retries = settings.provider_max_retries if max_retries is None else max_retries

    async def run(
        self,
        *,
        dependency: str,
        operation: str,
        call: Callable[[], Awaitable[T]],
    ) -> T:
        last_error: WorkflowProviderError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                result = await asyncio.wait_for(call(), timeout=self.timeout_seconds)
                await update_dependency_health(dependency=dependency, state="healthy")
                return result
            except WorkflowProviderError as exc:
                last_error = exc
                await update_dependency_health(dependency=dependency, state="degraded", failure=True)
                if not exc.retryable or attempt >= self.max_retries:
                    raise
            except TimeoutError as exc:
                last_error = WorkflowProviderError(
                    f"{operation}_timeout",
                    f"{operation} timed out.",
                    retryable=True,
                )
                await update_dependency_health(dependency=dependency, state="degraded", failure=True)
                if attempt >= self.max_retries:
                    raise last_error from exc
            except Exception as exc:
                last_error = WorkflowProviderError(
                    f"{operation}_unavailable",
                    f"{operation} is temporarily unavailable.",
                    retryable=True,
                )
                await update_dependency_health(dependency=dependency, state="degraded", failure=True)
                if attempt >= self.max_retries:
                    raise last_error from exc

        raise last_error or WorkflowProviderError(
            f"{operation}_unavailable",
            f"{operation} is temporarily unavailable.",
            retryable=True,
        )
