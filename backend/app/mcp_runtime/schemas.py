from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MCPToolCallTrace(BaseModel):
    tool_name: str = Field(alias="toolName")
    dependency: str
    operation: str
    allowed: bool = True
    redacted_error_code: str | None = Field(default=None, alias="redactedErrorCode")

    model_config = ConfigDict(populate_by_name=True)
