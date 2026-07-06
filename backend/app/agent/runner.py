from app.agent.graph import DiscoveryClientFactory, ExtractionClientFactory, RankingClientFactory, build_product_research_graph
from app.mcp_servers.discovery.client import build_discovery_tool_client
from app.mcp_servers.extraction.client import build_extraction_tool_client
from app.mcp_servers.ranking.client import build_ranking_tool_client
from app.workflow_contracts import WorkflowResult


class AgentJobRunner:
    def __init__(
        self,
        *,
        extraction_client_factory: ExtractionClientFactory | None = None,
        discovery_client_factory: DiscoveryClientFactory | None = None,
        ranking_client_factory: RankingClientFactory | None = None,
    ) -> None:
        self.extraction_client_factory = extraction_client_factory or build_extraction_tool_client
        self.discovery_client_factory = discovery_client_factory or build_discovery_tool_client
        self.ranking_client_factory = ranking_client_factory or build_ranking_tool_client
        self.graph = build_product_research_graph(
            self.extraction_client_factory,
            self.discovery_client_factory,
            self.ranking_client_factory,
        )

    async def run(self, job_id: str) -> WorkflowResult:
        state = await self.graph.ainvoke({"job_id": job_id})
        workflow_result = state.get("workflow_result") or {
            "jobId": job_id,
            "status": "failed",
        }
        return WorkflowResult.model_validate(workflow_result)


async def run_agent_job(job_id: str) -> WorkflowResult:
    return await AgentJobRunner().run(job_id)
