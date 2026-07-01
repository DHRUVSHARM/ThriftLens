from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ProductReference(BaseModel):
    product_type: str = Field(alias="productType", min_length=1)
    title: str = Field(min_length=1)
    brand: str | None = None
    color: str | None = None
    materials: list[str] = Field(default_factory=list)
    key_features: list[str] = Field(default_factory=list, alias="keyFeatures")
    search_queries: list[str] = Field(default_factory=list, alias="searchQueries")
    confidence: float = Field(default=0.75, ge=0, le=1)
    assumptions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class SourceProduct(BaseModel):
    source: str
    title: str
    retailer: str | None = None
    url: str | None = None
    price: float | None = Field(default=None, ge=0)
    currency: str = "USD"
    image_url: str | None = Field(default=None, alias="imageUrl")
    availability: str | None = None
    freshness: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class RankedProduct(BaseModel):
    product: SourceProduct
    score: float = Field(ge=0, le=1)
    group: Literal["closest", "cheaper", "similar", "premium", "possible"]
    confidence: Literal["high", "medium", "low"]
    reason: str


class ProductResearchBrief(BaseModel):
    mode: str
    label: str
    product_reference: ProductReference = Field(alias="productReference")
    trust_summary: str = Field(alias="trustSummary")
    source_count: int = Field(alias="sourceCount", ge=0)
    freshness_note: str = Field(alias="freshnessNote")
    uncertainty_notes: list[str] = Field(default_factory=list, alias="uncertaintyNotes")
    ranked_products: list[RankedProduct] = Field(default_factory=list, alias="rankedProducts")
    user_actions: list[str] = Field(default_factory=list, alias="userActions")
    status_reason: str | None = Field(default=None, alias="statusReason")

    model_config = ConfigDict(populate_by_name=True)


class WorkflowProviderError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ExtractionOutputError(Exception):
    pass


class WorkflowResult(BaseModel):
    job_id: str = Field(alias="jobId")
    status: str

    model_config = ConfigDict(populate_by_name=True)


def model_dump_alias(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(by_alias=True)
