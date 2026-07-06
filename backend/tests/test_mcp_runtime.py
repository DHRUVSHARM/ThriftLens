import pytest

from app.mcp_runtime.client import MCPRuntime
from app.mcp_runtime.registry import MCPToolRegistry, namespaced_tool_name
from app.mcp_runtime.tool_errors import MCP_TOOL_ERROR_KEY, run_mcp_tool
from app.workflow_contracts import WorkflowProviderError


class FakeTool:
    def __init__(self, name: str = "search") -> None:
        self.name = name
        self.calls: list[dict] = []

    async def ainvoke(self, payload: dict) -> dict:
        self.calls.append(payload)
        return {"ok": True, "payload": payload}


class FakeClient:
    def __init__(self, tools: list[FakeTool]) -> None:
        self.tools = tools
        self.get_tools_calls = 0

    async def get_tools(self) -> list[FakeTool]:
        self.get_tools_calls += 1
        return self.tools


class RecordingPolicy:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def run(self, *, dependency: str, operation: str, call):  # type: ignore[no-untyped-def]
        self.calls.append({"dependency": dependency, "operation": operation})
        return await call()


class NamedPolicy:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    async def run(self, *, dependency: str, operation: str, call):  # type: ignore[no-untyped-def]
        self.calls += 1
        result = await call()
        result["policy"] = self.name
        return result


@pytest.mark.anyio
async def test_mcp_runtime_invokes_allowlisted_tool_through_policy() -> None:
    search_tool = FakeTool("search")
    fake_client = FakeClient([search_tool])
    created_clients: list[dict] = []
    policy = RecordingPolicy()

    def client_factory(config: dict, handle_tool_errors: bool) -> FakeClient:
        created_clients.append({"config": config, "handle_tool_errors": handle_tool_errors})
        return fake_client

    runtime = MCPRuntime(
        connection_config={"serpapi": {"transport": "http", "url": "https://mcp.serpapi.com/key/mcp"}},
        allowed_tools={namespaced_tool_name("serpapi", "search")},
        policy=policy,  # type: ignore[arg-type]
        client_factory=client_factory,
    )

    result = await runtime.invoke_tool(
        namespaced_name="serpapi.search",
        payload={"params": {"q": "desk lamp"}},
        dependency="serpapi",
        operation="serpapi_research",
    )

    assert result["ok"] is True
    assert search_tool.calls == [{"params": {"q": "desk lamp"}}]
    assert policy.calls == [{"dependency": "serpapi", "operation": "serpapi_research"}]
    assert fake_client.get_tools_calls == 1
    assert created_clients == [
        {
            "config": {"serpapi": {"transport": "http", "url": "https://mcp.serpapi.com/key/mcp"}},
            "handle_tool_errors": False,
        }
    ]


@pytest.mark.anyio
async def test_mcp_runtime_allows_per_call_policy_override() -> None:
    search_tool = FakeTool("search")
    default_policy = NamedPolicy("default")
    override_policy = NamedPolicy("override")
    runtime = MCPRuntime(
        connection_config={"serpapi": {"transport": "http", "url": "https://mcp.serpapi.com/key/mcp"}},
        allowed_tools={namespaced_tool_name("serpapi", "search")},
        policy=default_policy,  # type: ignore[arg-type]
        client_factory=lambda _config, _handle_tool_errors: FakeClient([search_tool]),
    )

    result = await runtime.invoke_tool(
        namespaced_name="serpapi.search",
        payload={"params": {"q": "desk lamp"}},
        dependency="serpapi",
        operation="serpapi_research",
        policy=override_policy,  # type: ignore[arg-type]
    )

    assert result["policy"] == "override"
    assert default_policy.calls == 0
    assert override_policy.calls == 1


@pytest.mark.anyio
async def test_mcp_runtime_blocks_non_allowlisted_tool_before_invocation() -> None:
    search_tool = FakeTool("search")
    policy = RecordingPolicy()
    runtime = MCPRuntime(
        connection_config={"serpapi": {"transport": "http", "url": "https://mcp.serpapi.com/key/mcp"}},
        allowed_tools={"serpapi.search"},
        policy=policy,  # type: ignore[arg-type]
        client_factory=lambda _config, _handle_tool_errors: FakeClient([search_tool]),
    )

    with pytest.raises(WorkflowProviderError) as exc:
        await runtime.invoke_tool(
            namespaced_name="serpapi.delete_everything",
            payload={},
            dependency="serpapi",
            operation="serpapi_research",
        )

    assert exc.value.code == "mcp_tool_not_allowed"
    assert exc.value.retryable is False
    assert search_tool.calls == []


def test_mcp_runtime_redacts_secret_bearing_connection_summary() -> None:
    runtime = MCPRuntime(
        connection_config={
            "serpapi": {
                "transport": "http",
                "url": "https://mcp.serpapi.com/secret-serpapi-key/mcp",
            }
        },
        allowed_tools={"serpapi.search"},
        secrets=("secret-serpapi-key",),
    )

    assert runtime.sanitized_connection_summary() == {
        "serpapi": {
            "transport": "http",
            "url": "https://mcp.serpapi.com/[REDACTED]/mcp",
        }
    }


def test_mcp_tool_registry_reports_missing_tool() -> None:
    registry = MCPToolRegistry(tools=[FakeTool("search")], allowed_tools={"serpapi.lookup"})

    with pytest.raises(WorkflowProviderError) as exc:
        registry.get_tool("serpapi.lookup")

    assert exc.value.code == "mcp_tool_missing"
    assert exc.value.retryable is True


@pytest.mark.anyio
async def test_run_mcp_tool_returns_structured_safe_tool_error() -> None:
    async def failing_call() -> dict:
        raise WorkflowProviderError("provider_unavailable", "Provider is temporarily unavailable.", retryable=True)

    result = await run_mcp_tool(
        tool_name="screen_image_safety",
        dependency="gemini",
        operation="gemini_image_safety",
        call=failing_call(),
    )

    assert result[MCP_TOOL_ERROR_KEY] == {
        "code": "provider_unavailable",
        "message": "Provider is temporarily unavailable.",
        "retryable": True,
        "dependency": "gemini",
        "operation": "gemini_image_safety",
        "originCode": "provider_unavailable",
    }
