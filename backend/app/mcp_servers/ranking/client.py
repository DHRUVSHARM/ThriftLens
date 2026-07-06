from __future__ import annotations

from typing import Any, Protocol

from app.config import get_settings
from app.mcp_runtime.client import MCPRuntime
from app.mcp_runtime.registry import namespaced_tool_name
from app.mcp_servers.discovery.client import coerce_mcp_list_result
from app.mcp_servers.extraction.client import coerce_mcp_structured_result
from app.tool_policy import ToolExecutionPolicy
from app.workflow_contracts import ProductDiscoveryProfile, ProductReference, ProductSearchContext, RankedProduct, SourceProduct


RANKING_SERVER_NAME = "ranking"
SCORE_CANDIDATES_TOOL = namespaced_tool_name(RANKING_SERVER_NAME, "score_candidates")
DETECT_MISMATCHES_TOOL = namespaced_tool_name(RANKING_SERVER_NAME, "detect_mismatches")
GROUP_CANDIDATES_TOOL = namespaced_tool_name(RANKING_SERVER_NAME, "group_candidates")
EXPLAIN_MATCH_TOOL = namespaced_tool_name(RANKING_SERVER_NAME, "explain_match")

RANKING_ALLOWED_TOOLS = {
    SCORE_CANDIDATES_TOOL,
    DETECT_MISMATCHES_TOOL,
    GROUP_CANDIDATES_TOOL,
    EXPLAIN_MATCH_TOOL,
}


class RankingToolClientProtocol(Protocol):
    async def score_candidates(
        self,
        *,
        product_reference: ProductReference,
        product_profile: ProductDiscoveryProfile | None,
        search_context: ProductSearchContext | None,
        source_products: list[SourceProduct],
        preferences: dict[str, Any],
    ) -> list[RankedProduct]:
        ...

    async def detect_mismatches(
        self,
        *,
        product_reference: ProductReference,
        product_profile: ProductDiscoveryProfile | None,
        search_context: ProductSearchContext | None,
        ranked_products: list[RankedProduct],
    ) -> list[RankedProduct]:
        ...

    async def group_candidates(
        self,
        *,
        ranked_products: list[RankedProduct],
        preferences: dict[str, Any],
    ) -> list[RankedProduct]:
        ...

    async def explain_match(
        self,
        *,
        product_reference: ProductReference,
        product_profile: ProductDiscoveryProfile | None,
        search_context: ProductSearchContext | None,
        ranked_products: list[RankedProduct],
    ) -> dict[str, str]:
        ...


class RankingMCPToolClient:
    def __init__(self, *, runtime: MCPRuntime | None = None, policy: ToolExecutionPolicy | None = None) -> None:
        self.settings = get_settings()
        self.policy = policy or ToolExecutionPolicy()
        self.runtime = runtime or self.build_mcp_runtime()

    def build_mcp_runtime(self) -> MCPRuntime:
        return MCPRuntime(
            connection_config={
                RANKING_SERVER_NAME: {
                    "transport": "http",
                    "url": self.settings.ranking_mcp_url,
                }
            },
            allowed_tools=RANKING_ALLOWED_TOOLS,
            policy=self.policy,
            secrets=(self.settings.gemini_provider_api_key(),),
        )

    async def score_candidates(
        self,
        *,
        product_reference: ProductReference,
        product_profile: ProductDiscoveryProfile | None,
        search_context: ProductSearchContext | None,
        source_products: list[SourceProduct],
        preferences: dict[str, Any],
    ) -> list[RankedProduct]:
        result = await self.runtime.invoke_tool(
            namespaced_name=SCORE_CANDIDATES_TOOL,
            payload={
                "product_reference": product_reference.model_dump(by_alias=True),
                "product_profile": product_profile.model_dump(by_alias=True) if product_profile else None,
                "search_context": search_context.model_dump(by_alias=True) if search_context else None,
                "source_products": [product.model_dump(by_alias=True) for product in source_products],
                "preferences": preferences,
            },
            dependency="ranking-mcp",
            operation="score_candidates",
        )
        return [RankedProduct.model_validate(item) for item in coerce_mcp_list_result(result)]

    async def detect_mismatches(
        self,
        *,
        product_reference: ProductReference,
        product_profile: ProductDiscoveryProfile | None,
        search_context: ProductSearchContext | None,
        ranked_products: list[RankedProduct],
    ) -> list[RankedProduct]:
        result = await self.runtime.invoke_tool(
            namespaced_name=DETECT_MISMATCHES_TOOL,
            payload={
                "product_reference": product_reference.model_dump(by_alias=True),
                "product_profile": product_profile.model_dump(by_alias=True) if product_profile else None,
                "search_context": search_context.model_dump(by_alias=True) if search_context else None,
                "ranked_products": [product.model_dump(by_alias=True) for product in ranked_products],
            },
            dependency="ranking-mcp",
            operation="detect_mismatches",
        )
        return [RankedProduct.model_validate(item) for item in coerce_mcp_list_result(result)]

    async def group_candidates(
        self,
        *,
        ranked_products: list[RankedProduct],
        preferences: dict[str, Any],
    ) -> list[RankedProduct]:
        result = await self.runtime.invoke_tool(
            namespaced_name=GROUP_CANDIDATES_TOOL,
            payload={
                "ranked_products": [product.model_dump(by_alias=True) for product in ranked_products],
                "preferences": preferences,
            },
            dependency="ranking-mcp",
            operation="group_candidates",
        )
        return [RankedProduct.model_validate(item) for item in coerce_mcp_list_result(result)]

    async def explain_match(
        self,
        *,
        product_reference: ProductReference,
        product_profile: ProductDiscoveryProfile | None,
        search_context: ProductSearchContext | None,
        ranked_products: list[RankedProduct],
    ) -> dict[str, str]:
        result = await self.runtime.invoke_tool(
            namespaced_name=EXPLAIN_MATCH_TOOL,
            payload={
                "product_reference": product_reference.model_dump(by_alias=True),
                "product_profile": product_profile.model_dump(by_alias=True) if product_profile else None,
                "search_context": search_context.model_dump(by_alias=True) if search_context else None,
                "ranked_products": [product.model_dump(by_alias=True) for product in ranked_products],
            },
            dependency="ranking-mcp",
            operation="explain_match",
        )
        return dict(coerce_mcp_structured_result(result))


def build_ranking_tool_client() -> RankingToolClientProtocol:
    return RankingMCPToolClient()
