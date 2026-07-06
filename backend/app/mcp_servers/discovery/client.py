from __future__ import annotations

import json
from typing import Any, Protocol

from app.config import get_settings
from app.mcp_runtime.client import MCPRuntime
from app.mcp_runtime.registry import namespaced_tool_name
from app.mcp_servers.extraction.client import coerce_mcp_structured_result
from app.tool_policy import ToolExecutionPolicy
from app.workflow_contracts import (
    ProductDiscoveryProfile,
    ProductReference,
    ProductSearchContext,
    ProductSearchExecutionResult,
    ProductSearchPlan,
    SourceProduct,
)


DISCOVERY_SERVER_NAME = "discovery"
CLASSIFY_PRODUCT_PROFILE_TOOL = namespaced_tool_name(DISCOVERY_SERVER_NAME, "classify_product_profile")
BUILD_SEARCH_CONTEXT_TOOL = namespaced_tool_name(DISCOVERY_SERVER_NAME, "build_search_context")
PLAN_SEARCH_SOURCES_TOOL = namespaced_tool_name(DISCOVERY_SERVER_NAME, "plan_search_sources")
EXECUTE_SEARCH_PLAN_TOOL = namespaced_tool_name(DISCOVERY_SERVER_NAME, "execute_search_plan")
NORMALIZE_PRODUCTS_TOOL = namespaced_tool_name(DISCOVERY_SERVER_NAME, "normalize_products")
VERIFY_SOURCE_TOOL = namespaced_tool_name(DISCOVERY_SERVER_NAME, "verify_source")

DISCOVERY_ALLOWED_TOOLS = {
    CLASSIFY_PRODUCT_PROFILE_TOOL,
    BUILD_SEARCH_CONTEXT_TOOL,
    PLAN_SEARCH_SOURCES_TOOL,
    EXECUTE_SEARCH_PLAN_TOOL,
    NORMALIZE_PRODUCTS_TOOL,
    VERIFY_SOURCE_TOOL,
}


class DiscoveryToolClientProtocol(Protocol):
    async def classify_product_profile(
        self,
        *,
        product_reference: ProductReference,
        preferences: dict[str, Any],
    ) -> ProductDiscoveryProfile:
        ...

    async def build_search_context(
        self,
        *,
        product_reference: ProductReference,
        product_profile: ProductDiscoveryProfile,
    ) -> ProductSearchContext:
        ...

    async def plan_search_sources(
        self,
        *,
        product_reference: ProductReference,
        product_profile: ProductDiscoveryProfile,
        search_context: ProductSearchContext,
        preferences: dict[str, Any],
    ) -> ProductSearchPlan:
        ...

    async def execute_search_plan(self, *, search_plan: ProductSearchPlan) -> ProductSearchExecutionResult:
        ...

    async def normalize_products(self, *, search_results: ProductSearchExecutionResult) -> list[SourceProduct]:
        ...


class DiscoveryMCPToolClient:
    def __init__(self, *, runtime: MCPRuntime | None = None, policy: ToolExecutionPolicy | None = None) -> None:
        self.settings = get_settings()
        self.policy = policy or ToolExecutionPolicy()
        self.runtime = runtime or self.build_mcp_runtime()

    def build_mcp_runtime(self) -> MCPRuntime:
        return MCPRuntime(
            connection_config={
                DISCOVERY_SERVER_NAME: {
                    "transport": "http",
                    "url": self.settings.discovery_mcp_endpoint(),
                }
            },
            allowed_tools=DISCOVERY_ALLOWED_TOOLS,
            policy=self.policy,
            secrets=(self.settings.serpapi_api_key,),
        )

    async def classify_product_profile(
        self,
        *,
        product_reference: ProductReference,
        preferences: dict[str, Any],
    ) -> ProductDiscoveryProfile:
        result = await self.runtime.invoke_tool(
            namespaced_name=CLASSIFY_PRODUCT_PROFILE_TOOL,
            payload={"product_reference": product_reference.model_dump(by_alias=True), "preferences": preferences},
            dependency="discovery-mcp",
            operation="classify_product_profile",
        )
        return ProductDiscoveryProfile.model_validate(coerce_mcp_structured_result(result))

    async def build_search_context(
        self,
        *,
        product_reference: ProductReference,
        product_profile: ProductDiscoveryProfile,
    ) -> ProductSearchContext:
        result = await self.runtime.invoke_tool(
            namespaced_name=BUILD_SEARCH_CONTEXT_TOOL,
            payload={
                "product_reference": product_reference.model_dump(by_alias=True),
                "product_profile": product_profile.model_dump(by_alias=True),
            },
            dependency="discovery-mcp",
            operation="build_search_context",
        )
        return ProductSearchContext.model_validate(coerce_mcp_structured_result(result))

    async def plan_search_sources(
        self,
        *,
        product_reference: ProductReference,
        product_profile: ProductDiscoveryProfile,
        search_context: ProductSearchContext,
        preferences: dict[str, Any],
    ) -> ProductSearchPlan:
        result = await self.runtime.invoke_tool(
            namespaced_name=PLAN_SEARCH_SOURCES_TOOL,
            payload={
                "product_reference": product_reference.model_dump(by_alias=True),
                "product_profile": product_profile.model_dump(by_alias=True),
                "search_context": search_context.model_dump(by_alias=True),
                "preferences": preferences,
            },
            dependency="discovery-mcp",
            operation="plan_search_sources",
        )
        return ProductSearchPlan.model_validate(coerce_mcp_structured_result(result))

    async def execute_search_plan(self, *, search_plan: ProductSearchPlan) -> ProductSearchExecutionResult:
        execution_policy = ToolExecutionPolicy(timeout_seconds=search_plan_timeout_seconds(search_plan))
        result = await self.runtime.invoke_tool(
            namespaced_name=EXECUTE_SEARCH_PLAN_TOOL,
            payload={"search_plan": search_plan.model_dump(by_alias=True)},
            dependency="discovery-mcp",
            operation="execute_search_plan",
            policy=execution_policy,
        )
        return ProductSearchExecutionResult.model_validate(coerce_mcp_structured_result(result))

    async def normalize_products(self, *, search_results: ProductSearchExecutionResult) -> list[SourceProduct]:
        result = await self.runtime.invoke_tool(
            namespaced_name=NORMALIZE_PRODUCTS_TOOL,
            payload={"search_results": search_results.model_dump(by_alias=True)},
            dependency="discovery-mcp",
            operation="normalize_products",
        )
        coerced = coerce_mcp_list_result(result)
        return [SourceProduct.model_validate(item) for item in coerced]


def build_discovery_tool_client() -> DiscoveryToolClientProtocol:
    return DiscoveryMCPToolClient()


def search_plan_timeout_seconds(search_plan: ProductSearchPlan) -> float:
    settings = get_settings()
    planned_calls = min(max(len(search_plan.plan_items), 1), settings.serpapi_max_calls_per_job)
    attempts_per_call = settings.provider_max_retries + 1
    retry_gaps = max(0, settings.provider_max_retries) * settings.provider_backoff_base_seconds
    per_call_budget = (settings.provider_timeout_seconds * attempts_per_call) + retry_gaps
    return per_call_budget * planned_calls + 5


def coerce_mcp_list_result(result: Any) -> list[Any]:
    if isinstance(result, tuple) and len(result) == 2:
        content, artifact = result
        artifact_content = coerce_mcp_list_result(artifact)
        if artifact_content:
            return artifact_content
        return coerce_mcp_list_result(content)

    if isinstance(result, list):
        if all(isinstance(item, dict) and item.get("type") != "text" for item in result):
            return result
        collected: list[Any] = []
        for item in result:
            coerced = coerce_mcp_list_result(item)
            if coerced:
                collected.extend(coerced)
        return collected

    if isinstance(result, dict):
        if "structured_content" in result:
            return coerce_mcp_list_result(result["structured_content"])
        if "structuredContent" in result:
            return coerce_mcp_list_result(result["structuredContent"])
        if result.get("type") == "text":
            return coerce_mcp_list_result(result.get("text"))
        return [result]

    if isinstance(result, str) and result.strip():
        parsed = json.loads(result)
        return parsed if isinstance(parsed, list) else [parsed]

    return []
