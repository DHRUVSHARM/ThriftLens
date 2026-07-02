from app.config import get_settings
from app.gemini_provider import GeminiExtractionProvider, GeminiRankingExplainer
from app.sample_providers import SampleExtractionProvider, SampleResearchProvider
from app.serpapi_provider import SerpApiMCPResearchProvider
from app.workflow import ResearchWorkflow


def build_research_workflow() -> ResearchWorkflow:
    settings = get_settings()
    if settings.provider_mode == "REAL_MODE":
        return ResearchWorkflow(
            extraction_provider=GeminiExtractionProvider(),
            research_provider=SerpApiMCPResearchProvider(),
            ranking_explainer=GeminiRankingExplainer() if settings.gemini_ranking_enabled else None,
        )
    return ResearchWorkflow(
        extraction_provider=SampleExtractionProvider(),
        research_provider=SampleResearchProvider(),
    )
