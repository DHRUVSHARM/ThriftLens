from __future__ import annotations

import json
from typing import Any, Protocol

from app.config import get_settings
from app.mcp_runtime.client import MCPRuntime
from app.mcp_runtime.registry import namespaced_tool_name
from app.tool_policy import ToolExecutionPolicy
from app.workflow_contracts import (
    ImageGateResult,
    ImageSafetyResult,
    ProductReference,
    TargetProductSelection,
    TextSafetyResult,
    WorkflowProviderError,
)


EXTRACTION_SERVER_NAME = "extraction"
SCREEN_IMAGE_SAFETY_TOOL = namespaced_tool_name(EXTRACTION_SERVER_NAME, "screen_image_safety")
SCREEN_TEXT_SAFETY_TOOL = namespaced_tool_name(EXTRACTION_SERVER_NAME, "screen_text_safety")
IMAGE_PRODUCT_GATE_TOOL = namespaced_tool_name(EXTRACTION_SERVER_NAME, "image_product_gate")
EXTRACT_PRODUCT_REFERENCE_TOOL = namespaced_tool_name(EXTRACTION_SERVER_NAME, "extract_product_reference")
REPAIR_PRODUCT_REFERENCE_TOOL = namespaced_tool_name(EXTRACTION_SERVER_NAME, "repair_product_reference")
DISAMBIGUATE_TARGET_PRODUCT_TOOL = namespaced_tool_name(EXTRACTION_SERVER_NAME, "disambiguate_target_product")

EXTRACTION_ALLOWED_TOOLS = {
    SCREEN_IMAGE_SAFETY_TOOL,
    SCREEN_TEXT_SAFETY_TOOL,
    IMAGE_PRODUCT_GATE_TOOL,
    EXTRACT_PRODUCT_REFERENCE_TOOL,
    REPAIR_PRODUCT_REFERENCE_TOOL,
    DISAMBIGUATE_TARGET_PRODUCT_TOOL,
}


class ExtractionToolClientProtocol(Protocol):
    async def screen_image_safety(
        self,
        *,
        request_payload: dict[str, Any],
        image_metadata: list[dict[str, Any]],
    ) -> ImageSafetyResult:
        ...

    async def screen_text_safety(self, *, request_payload: dict[str, Any]) -> TextSafetyResult:
        ...

    async def image_product_gate(
        self,
        *,
        request_payload: dict[str, Any],
        image_metadata: list[dict[str, Any]],
    ) -> ImageGateResult:
        ...

    async def extract_product_reference(
        self,
        *,
        input_type: str,
        request_payload: dict[str, Any],
        image_metadata: list[dict[str, Any]],
    ) -> ProductReference:
        ...

    async def repair_product_reference(self, *, raw_output: dict[str, Any]) -> ProductReference:
        ...

    async def disambiguate_target_product(
        self,
        *,
        detected_products: list[dict[str, Any]],
        target_description: str | None = None,
    ) -> TargetProductSelection:
        ...


class ExtractionMCPToolClient:
    def __init__(self, *, runtime: MCPRuntime | None = None, policy: ToolExecutionPolicy | None = None) -> None:
        self.settings = get_settings()
        self.policy = policy or ToolExecutionPolicy()
        self.runtime = runtime or self.build_mcp_runtime()

    def build_mcp_runtime(self) -> MCPRuntime:
        return MCPRuntime(
            connection_config={
                EXTRACTION_SERVER_NAME: {
                    "transport": "http",
                    "url": self.settings.extraction_mcp_endpoint(),
                }
            },
            allowed_tools=EXTRACTION_ALLOWED_TOOLS,
            policy=self.policy,
        )

    async def screen_image_safety(
        self,
        *,
        request_payload: dict[str, Any],
        image_metadata: list[dict[str, Any]],
    ) -> ImageSafetyResult:
        result = await self.runtime.invoke_tool(
            namespaced_name=SCREEN_IMAGE_SAFETY_TOOL,
            payload={"request_payload": request_payload, "image_metadata": image_metadata},
            dependency="extraction-mcp",
            operation="screen_image_safety",
        )
        return ImageSafetyResult.model_validate(coerce_mcp_structured_result(result))

    async def screen_text_safety(self, *, request_payload: dict[str, Any]) -> TextSafetyResult:
        result = await self.runtime.invoke_tool(
            namespaced_name=SCREEN_TEXT_SAFETY_TOOL,
            payload={"request_payload": request_payload},
            dependency="extraction-mcp",
            operation="screen_text_safety",
        )
        return TextSafetyResult.model_validate(coerce_mcp_structured_result(result))

    async def image_product_gate(
        self,
        *,
        request_payload: dict[str, Any],
        image_metadata: list[dict[str, Any]],
    ) -> ImageGateResult:
        result = await self.runtime.invoke_tool(
            namespaced_name=IMAGE_PRODUCT_GATE_TOOL,
            payload={"request_payload": request_payload, "image_metadata": image_metadata},
            dependency="extraction-mcp",
            operation="image_product_gate",
        )
        return ImageGateResult.model_validate(coerce_mcp_structured_result(result))

    async def extract_product_reference(
        self,
        *,
        input_type: str,
        request_payload: dict[str, Any],
        image_metadata: list[dict[str, Any]],
    ) -> ProductReference:
        result = await self.runtime.invoke_tool(
            namespaced_name=EXTRACT_PRODUCT_REFERENCE_TOOL,
            payload={
                "input_type": input_type,
                "request_payload": request_payload,
                "image_metadata": image_metadata,
            },
            dependency="extraction-mcp",
            operation="extract_product_reference",
        )
        return ProductReference.model_validate(coerce_mcp_structured_result(result))

    async def repair_product_reference(self, *, raw_output: dict[str, Any]) -> ProductReference:
        result = await self.runtime.invoke_tool(
            namespaced_name=REPAIR_PRODUCT_REFERENCE_TOOL,
            payload={"raw_output": raw_output},
            dependency="extraction-mcp",
            operation="repair_product_reference",
        )
        return ProductReference.model_validate(coerce_mcp_structured_result(result))

    async def disambiguate_target_product(
        self,
        *,
        detected_products: list[dict[str, Any]],
        target_description: str | None = None,
    ) -> TargetProductSelection:
        result = await self.runtime.invoke_tool(
            namespaced_name=DISAMBIGUATE_TARGET_PRODUCT_TOOL,
            payload={"detected_products": detected_products, "target_description": target_description},
            dependency="extraction-mcp",
            operation="disambiguate_target_product",
        )
        return TargetProductSelection.model_validate(coerce_mcp_structured_result(result))


def build_extraction_tool_client() -> ExtractionToolClientProtocol:
    return ExtractionMCPToolClient()


def coerce_mcp_structured_result(result: Any) -> Any:
    if isinstance(result, tuple) and len(result) == 2:
        content, artifact = result
        structured_artifact = coerce_mcp_structured_result(artifact)
        if isinstance(structured_artifact, dict):
            return structured_artifact
        return coerce_mcp_structured_result(content)

    if isinstance(result, dict):
        if "structured_content" in result:
            return result["structured_content"]
        if "structuredContent" in result:
            return result["structuredContent"]
        if result.get("type") == "text":
            return parse_mcp_json_text(result.get("text"))
        return result

    if isinstance(result, list):
        for item in result:
            coerced = coerce_mcp_structured_result(item)
            if isinstance(coerced, dict):
                return coerced
        raise WorkflowProviderError("extraction_mcp_invalid_response", "Extraction MCP returned no JSON result.", retryable=True)

    if isinstance(result, str):
        return parse_mcp_json_text(result)

    return result


def parse_mcp_json_text(value: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowProviderError("extraction_mcp_invalid_response", "Extraction MCP returned empty text.", retryable=True)
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise WorkflowProviderError("extraction_mcp_invalid_response", "Extraction MCP returned malformed JSON.", retryable=True) from exc
