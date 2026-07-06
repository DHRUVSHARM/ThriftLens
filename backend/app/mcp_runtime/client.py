from collections.abc import Callable, Iterable, Sequence
from typing import Any, Protocol

from app.mcp_runtime.registry import MCPToolRegistry
from app.redaction import redact_provider_secrets
from app.tool_policy import ToolExecutionPolicy


class MCPClientProtocol(Protocol):
    async def get_tools(self) -> Sequence[Any]:
        ...


MCPClientFactory = Callable[[dict[str, Any], bool], MCPClientProtocol]


def default_mcp_client_factory(config: dict[str, Any], handle_tool_errors: bool) -> MCPClientProtocol:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    return MultiServerMCPClient(config, handle_tool_errors=handle_tool_errors)


class MCPRuntime:
    def __init__(
        self,
        *,
        connection_config: dict[str, Any],
        allowed_tools: Iterable[str],
        policy: ToolExecutionPolicy | None = None,
        secrets: Iterable[str] = (),
        client_factory: MCPClientFactory | None = None,
        handle_tool_errors: bool = False,
    ) -> None:
        self.connection_config = connection_config
        self.allowed_tools = set(allowed_tools)
        self.policy = policy or ToolExecutionPolicy()
        self.secrets = tuple(secrets)
        self.client_factory = client_factory or default_mcp_client_factory
        self.handle_tool_errors = handle_tool_errors
        self._client: MCPClientProtocol | None = None
        self._registry: MCPToolRegistry | None = None

    def sanitized_connection_summary(self) -> dict[str, Any]:
        return redact_nested(self.connection_config, secrets=self.secrets)

    async def get_registry(self) -> MCPToolRegistry:
        if self._registry is None:
            client = self._client or self.client_factory(self.connection_config, self.handle_tool_errors)
            self._client = client
            self._registry = MCPToolRegistry(
                tools=await client.get_tools(),
                allowed_tools=self.allowed_tools,
            )
        return self._registry

    async def invoke_tool(
        self,
        *,
        namespaced_name: str,
        payload: dict[str, Any],
        dependency: str,
        operation: str,
        policy: ToolExecutionPolicy | None = None,
    ) -> Any:
        async def call() -> Any:
            registry = await self.get_registry()
            tool = registry.get_tool(namespaced_name)
            return await tool.ainvoke(payload)

        return await (policy or self.policy).run(dependency=dependency, operation=operation, call=call)


def redact_nested(value: Any, *, secrets: Iterable[str]) -> Any:
    if isinstance(value, dict):
        return {key: redact_nested(child, secrets=secrets) for key, child in value.items()}
    if isinstance(value, list):
        return [redact_nested(child, secrets=secrets) for child in value]
    if isinstance(value, tuple):
        return tuple(redact_nested(child, secrets=secrets) for child in value)
    if isinstance(value, str):
        return redact_provider_secrets(value, secrets=secrets)
    return value
