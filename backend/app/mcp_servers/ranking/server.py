from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.mcp_servers.ranking.tools import (
    detect_mismatches_tool,
    explain_match_tool,
    group_candidates_tool,
    score_candidates_tool,
)


MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8003"))
MCP_SERVER_PATH = os.getenv("MCP_SERVER_PATH", "/mcp")
MCP_SERVER_TRANSPORT = os.getenv("MCP_SERVER_TRANSPORT", "streamable-http")


mcp = FastMCP(
    "thriftlens-product-ranking",
    host=MCP_SERVER_HOST,
    port=MCP_SERVER_PORT,
    streamable_http_path=MCP_SERVER_PATH,
)


@mcp.tool(name="score_candidates")
async def score_candidates(
    product_reference: dict[str, Any],
    product_profile: dict[str, Any] | None,
    search_context: dict[str, Any] | None,
    source_products: list[dict[str, Any]],
    preferences: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return await score_candidates_tool(
        product_reference=product_reference,
        product_profile=product_profile,
        search_context=search_context,
        source_products=source_products,
        preferences=preferences,
    )


@mcp.tool(name="detect_mismatches")
async def detect_mismatches(
    product_reference: dict[str, Any],
    product_profile: dict[str, Any] | None,
    search_context: dict[str, Any] | None,
    ranked_products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return await detect_mismatches_tool(
        product_reference=product_reference,
        product_profile=product_profile,
        search_context=search_context,
        ranked_products=ranked_products,
    )


@mcp.tool(name="group_candidates")
async def group_candidates(
    ranked_products: list[dict[str, Any]],
    preferences: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return await group_candidates_tool(ranked_products=ranked_products, preferences=preferences)


@mcp.tool(name="explain_match")
async def explain_match(
    product_reference: dict[str, Any],
    product_profile: dict[str, Any] | None,
    search_context: dict[str, Any] | None,
    ranked_products: list[dict[str, Any]],
) -> dict[str, str]:
    return await explain_match_tool(
        product_reference=product_reference,
        product_profile=product_profile,
        search_context=search_context,
        ranked_products=ranked_products,
    )


if __name__ == "__main__":
    mcp.run(transport=MCP_SERVER_TRANSPORT)
