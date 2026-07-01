from typing import Any

from app.config import get_settings
from app.tool_policy import ToolExecutionPolicy
from app.workflow_contracts import ProductReference, WorkflowProviderError

ALLOWED_ENGINE = "google_shopping"
ALLOWED_PARAM_KEYS = {"engine", "q", "location", "gl", "hl", "num"}


class SerpApiMCPResearchProvider:
    def __init__(self, *, policy: ToolExecutionPolicy | None = None) -> None:
        self.settings = get_settings()
        self.policy = policy or ToolExecutionPolicy()

    def mcp_connection_config(self) -> dict[str, Any]:
        if not self.settings.serpapi_api_key:
            raise WorkflowProviderError(
                "serpapi_configuration_missing",
                "SerpAPI API key is required for live research.",
                retryable=False,
            )
        return {
            "serpapi": {
                "transport": "http",
                "url": self.settings.build_serpapi_mcp_url(),
            }
        }

    def sanitized_connection_summary(self) -> dict[str, str]:
        return {"server": "serpapi", "transport": "http", "auth": "configured" if self.settings.serpapi_api_key else "missing"}

    def build_search_params(self, *, query: str, preferences: dict[str, Any]) -> dict[str, Any]:
        params = {
            "engine": ALLOWED_ENGINE,
            "q": query,
            "num": 10,
        }
        if preferences.get("location"):
            params["location"] = preferences["location"]
        if preferences.get("marketplace"):
            params["gl"] = preferences["marketplace"]
        return {key: value for key, value in params.items() if key in ALLOWED_PARAM_KEYS and value}

    async def research(self, product_reference: ProductReference, preferences: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.settings.serpapi_api_key:
            raise WorkflowProviderError(
                "serpapi_configuration_missing",
                "SerpAPI API key is required for live research.",
                retryable=False,
            )

        async def call() -> list[dict[str, Any]]:
            return await self._research_with_mcp(product_reference, preferences)

        return await self.policy.run(dependency="serpapi", operation="serpapi_research", call=call)

    async def _research_with_mcp(self, product_reference: ProductReference, preferences: dict[str, Any]) -> list[dict[str, Any]]:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        client = MultiServerMCPClient(self.mcp_connection_config(), handle_tool_errors=False)
        tools = await client.get_tools()
        search_tool = next((tool for tool in tools if tool.name == "search"), None)
        if search_tool is None:
            raise WorkflowProviderError("serpapi_search_tool_missing", "SerpAPI search tool is unavailable.", retryable=True)

        normalized: list[dict[str, Any]] = []
        queries = product_reference.search_queries or [product_reference.title]
        for query in queries[: self.settings.serpapi_max_calls_per_job]:
            params = self.build_search_params(query=query, preferences=preferences)
            result = await search_tool.ainvoke({"params": params})
            normalized.extend(normalize_serpapi_response(result))
        return normalized


def normalize_serpapi_response(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, str):
        raise WorkflowProviderError("serpapi_invalid_response", "SerpAPI returned an unstructured response.", retryable=True)
    if not isinstance(response, dict):
        raise WorkflowProviderError("serpapi_invalid_response", "SerpAPI returned an invalid response.", retryable=True)

    raw_items = response.get("shopping_results") or response.get("inline_shopping_results") or []
    if not isinstance(raw_items, list):
        raise WorkflowProviderError("serpapi_invalid_response", "SerpAPI results were not a list.", retryable=True)

    products: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        price = parse_source_price(item)
        products.append(
            {
                "source": "serpapi-google-shopping",
                "title": item.get("title") or item.get("name") or "Unknown product",
                "retailer": item.get("source") or item.get("seller"),
                "url": item.get("link") or item.get("product_link"),
                "price": price,
                "currency": "USD",
                "imageUrl": item.get("thumbnail") or item.get("image"),
                "availability": item.get("availability"),
                "freshness": "live",
            }
        )
    return products


def parse_source_price(item: dict[str, Any]) -> float | None:
    extracted = item.get("extracted_price")
    if isinstance(extracted, (int, float)):
        return float(extracted)
    price = item.get("price")
    if not isinstance(price, str):
        return None
    clean = price.replace("$", "").replace(",", "").strip()
    try:
        return float(clean.split()[0])
    except (ValueError, IndexError):
        return None
