from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.logging_config import configure_secret_redaction_logging
from app.mcp_runtime.tool_errors import run_mcp_tool
from app.mcp_servers.discovery.tools import (
    build_search_context_tool,
    classify_product_profile_tool,
    execute_search_plan_tool,
    normalize_products_tool,
    plan_search_sources_tool,
    verify_source_tool,
)

configure_secret_redaction_logging()


MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8002"))
MCP_SERVER_PATH = os.getenv("MCP_SERVER_PATH", "/mcp")
MCP_SERVER_TRANSPORT = os.getenv("MCP_SERVER_TRANSPORT", "streamable-http")


mcp = FastMCP(
    "thriftlens-product-discovery",
    host=MCP_SERVER_HOST,
    port=MCP_SERVER_PORT,
    streamable_http_path=MCP_SERVER_PATH,
)


@mcp.tool(name="classify_product_profile")
async def classify_product_profile(product_reference: dict[str, Any], preferences: dict[str, Any] | None = None) -> dict[str, Any]:
    return await run_mcp_tool(
        tool_name="classify_product_profile",
        dependency="gemini",
        operation="discovery_profile_model",
        call=classify_product_profile_tool(product_reference=product_reference, preferences=preferences),
    )


@mcp.tool(name="build_search_context")
async def build_search_context(product_reference: dict[str, Any], product_profile: dict[str, Any]) -> dict[str, Any]:
    return await build_search_context_tool(product_reference=product_reference, product_profile=product_profile)


@mcp.tool(name="plan_search_sources")
async def plan_search_sources(
    product_reference: dict[str, Any],
    product_profile: dict[str, Any],
    search_context: dict[str, Any],
    preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await run_mcp_tool(
        tool_name="plan_search_sources",
        dependency="gemini",
        operation="discovery_search_plan_model",
        call=plan_search_sources_tool(
            product_reference=product_reference,
            product_profile=product_profile,
            search_context=search_context,
            preferences=preferences,
        ),
    )


@mcp.tool(name="execute_search_plan")
async def execute_search_plan(search_plan: dict[str, Any]) -> dict[str, Any]:
    return await run_mcp_tool(
        tool_name="execute_search_plan",
        dependency="serpapi",
        operation="discovery_search_sources",
        call=execute_search_plan_tool(search_plan=search_plan),
    )


@mcp.tool(name="normalize_products")
async def normalize_products(search_results: dict[str, Any]) -> list[dict[str, Any]]:
    return await normalize_products_tool(search_results=search_results)


@mcp.tool(name="verify_source")
async def verify_source(source_product: dict[str, Any]) -> dict[str, Any]:
    return await verify_source_tool(source_product=source_product)


if __name__ == "__main__":
    mcp.run(transport=MCP_SERVER_TRANSPORT)
