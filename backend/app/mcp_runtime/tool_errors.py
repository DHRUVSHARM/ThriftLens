from __future__ import annotations

import logging
from collections.abc import Awaitable
from typing import Any, TypeVar

from app.redaction import redact_provider_secrets
from app.tool_policy import classify_provider_error, classify_provider_exception
from app.workflow_contracts import WorkflowProviderError

MCP_TOOL_ERROR_KEY = "_thriftlensToolError"

T = TypeVar("T")
logger = logging.getLogger(__name__)


async def run_mcp_tool(
    *,
    tool_name: str,
    dependency: str,
    operation: str,
    call: Awaitable[T],
) -> T | dict[str, Any]:
    try:
        return await call
    except WorkflowProviderError as exc:
        error = classify_provider_error(exc)
        logger.warning(
            "MCP tool provider failure tool=%s dependency=%s operation=%s code=%s origin_code=%s retryable=%s",
            tool_name,
            dependency,
            operation,
            error.code,
            exc.code,
            error.retryable,
        )
        return mcp_tool_error_payload(error, dependency=dependency, operation=operation, origin_code=exc.code)
    except Exception as exc:
        error = classify_provider_exception(exc)
        logger.warning(
            "MCP tool unexpected provider failure tool=%s dependency=%s operation=%s code=%s exception_class=%s",
            tool_name,
            dependency,
            operation,
            error.code,
            exc.__class__.__name__,
        )
        return mcp_tool_error_payload(
            error,
            dependency=dependency,
            operation=operation,
            origin_code=exc.__class__.__name__,
        )


def mcp_tool_error_payload(
    error: WorkflowProviderError,
    *,
    dependency: str,
    operation: str,
    origin_code: str | None = None,
) -> dict[str, Any]:
    return {
        MCP_TOOL_ERROR_KEY: {
            "code": error.code,
            "message": redact_provider_secrets(str(error)),
            "retryable": error.retryable,
            "dependency": dependency,
            "operation": operation,
            "originCode": origin_code or error.code,
        }
    }


def raise_if_mcp_tool_error(value: Any) -> None:
    if not isinstance(value, dict) or MCP_TOOL_ERROR_KEY not in value:
        return

    payload = value.get(MCP_TOOL_ERROR_KEY)
    if not isinstance(payload, dict):
        raise WorkflowProviderError(
            "mcp_tool_invalid_error",
            "MCP tool returned malformed error metadata.",
            retryable=True,
        )

    code = str(payload.get("code") or "provider_unavailable")
    message = str(payload.get("message") or "Provider is temporarily unavailable.")
    retryable = bool(payload.get("retryable", True))
    error = WorkflowProviderError(code, message, retryable=retryable)
    setattr(error, "dependency", payload.get("dependency"))
    setattr(error, "operation", payload.get("operation"))
    setattr(error, "origin_code", payload.get("originCode"))
    raise error
