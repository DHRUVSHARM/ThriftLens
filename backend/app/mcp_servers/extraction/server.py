from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.logging_config import configure_secret_redaction_logging
from app.mcp_runtime.tool_errors import run_mcp_tool
from app.mcp_servers.extraction.tools import (
    disambiguate_target_product_tool,
    extract_product_reference_tool,
    image_product_gate_tool,
    repair_product_reference_tool,
    screen_image_safety_tool,
    screen_text_safety_tool,
)

configure_secret_redaction_logging()

MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8001"))
MCP_SERVER_PATH = os.getenv("MCP_SERVER_PATH", "/mcp")
MCP_SERVER_TRANSPORT = os.getenv("MCP_SERVER_TRANSPORT", "streamable-http")


mcp = FastMCP(
    "thriftlens-product-extraction",
    host=MCP_SERVER_HOST,
    port=MCP_SERVER_PORT,
    streamable_http_path=MCP_SERVER_PATH,
)


@mcp.tool(name="screen_image_safety")
async def screen_image_safety(request_payload: dict[str, Any], image_metadata: list[dict[str, Any]]) -> dict[str, Any]:
    return await run_mcp_tool(
        tool_name="screen_image_safety",
        dependency="gemini",
        operation="gemini_image_safety",
        call=screen_image_safety_tool(request_payload=request_payload, image_metadata=image_metadata),
    )


@mcp.tool(name="screen_text_safety")
async def screen_text_safety(request_payload: dict[str, Any]) -> dict[str, Any]:
    return await run_mcp_tool(
        tool_name="screen_text_safety",
        dependency="gemini",
        operation="gemini_text_safety",
        call=screen_text_safety_tool(request_payload=request_payload),
    )


@mcp.tool(name="image_product_gate")
async def image_product_gate(request_payload: dict[str, Any], image_metadata: list[dict[str, Any]]) -> dict[str, Any]:
    return await run_mcp_tool(
        tool_name="image_product_gate",
        dependency="gemini",
        operation="gemini_image_gate",
        call=image_product_gate_tool(request_payload=request_payload, image_metadata=image_metadata),
    )


@mcp.tool(name="extract_product_reference")
async def extract_product_reference(
    input_type: str,
    request_payload: dict[str, Any],
    image_metadata: list[dict[str, Any]],
) -> dict[str, Any]:
    return await run_mcp_tool(
        tool_name="extract_product_reference",
        dependency="gemini",
        operation="gemini_extraction",
        call=extract_product_reference_tool(
            input_type=input_type,
            request_payload=request_payload,
            image_metadata=image_metadata,
        ),
    )


@mcp.tool(name="repair_product_reference")
async def repair_product_reference(raw_output: dict[str, Any]) -> dict[str, Any]:
    return await run_mcp_tool(
        tool_name="repair_product_reference",
        dependency="gemini",
        operation="gemini_repair",
        call=repair_product_reference_tool(raw_output=raw_output),
    )


@mcp.tool(name="disambiguate_target_product")
async def disambiguate_target_product(
    detected_products: list[dict[str, Any]],
    target_description: str | None = None,
) -> dict[str, Any]:
    return await disambiguate_target_product_tool(
        detected_products=detected_products,
        target_description=target_description,
    )


if __name__ == "__main__":
    mcp.run(transport=MCP_SERVER_TRANSPORT)
