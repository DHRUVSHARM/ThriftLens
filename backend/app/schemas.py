from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


InputType = Literal["image", "text"]
JobStatus = Literal[
    "queued",
    "extracting_reference",
    "needs_refinement",
    "researching_sources",
    "ranking_results",
    "complete",
    "partial",
    "failed",
    "expired",
]


class ResearchPreferences(BaseModel):
    ranking_preference: Literal["closest", "grouped"] = Field(
        default="grouped",
        alias="rankingPreference",
    )
    budget_min: float | None = Field(default=None, ge=0, alias="budgetMin")
    budget_max: float | None = Field(default=None, ge=0, alias="budgetMax")
    marketplace: str | None = Field(default=None, max_length=80)
    location: str | None = Field(default=None, max_length=80)

    model_config = ConfigDict(populate_by_name=True)


class CreateResearchJobInput(BaseModel):
    input_type: InputType = Field(alias="inputType")
    text_description: str | None = Field(default=None, max_length=2000, alias="textDescription")
    target_description: str | None = Field(default=None, max_length=2000, alias="targetDescription")
    research_preferences: ResearchPreferences = Field(
        default_factory=ResearchPreferences,
        alias="researchPreferences",
    )

    model_config = ConfigDict(populate_by_name=True)


class SafeError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class ResearchJobResponse(BaseModel):
    job_id: str = Field(alias="jobId")
    status: JobStatus
    progress_message: str = Field(alias="progressMessage")
    retryable: bool
    provider_mode: str = Field(alias="providerMode")
    safe_error: SafeError | None = Field(default=None, alias="safeError")
    partial_brief: dict[str, Any] | None = Field(default=None, alias="partialBrief")
    final_brief: dict[str, Any] | None = Field(default=None, alias="finalBrief")

    model_config = ConfigDict(populate_by_name=True)


class CreateResearchJobResponse(ResearchJobResponse):
    pass
