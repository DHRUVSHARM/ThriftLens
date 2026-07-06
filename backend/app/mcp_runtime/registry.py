from collections.abc import Iterable, Sequence
from typing import Any

from app.workflow_contracts import WorkflowProviderError


def namespaced_tool_name(server_name: str, tool_name: str) -> str:
    return f"{server_name}.{tool_name}"


class MCPToolRegistry:
    def __init__(self, *, tools: Sequence[Any], allowed_tools: Iterable[str]) -> None:
        self.allowed_tools = set(allowed_tools)
        self.tools_by_name = {tool.name: tool for tool in tools}

    def get_tool(self, namespaced_name: str) -> Any:
        if namespaced_name not in self.allowed_tools:
            raise WorkflowProviderError(
                "mcp_tool_not_allowed",
                "Requested MCP tool is not allowlisted.",
                retryable=False,
            )

        tool_name = namespaced_name.rsplit(".", maxsplit=1)[-1]
        tool = self.tools_by_name.get(tool_name) or self.tools_by_name.get(namespaced_name)
        if tool is None:
            raise WorkflowProviderError(
                "mcp_tool_missing",
                "Requested MCP tool is unavailable.",
                retryable=True,
            )
        return tool

    def discovered_names(self) -> list[str]:
        return sorted(self.tools_by_name)
