from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    # Allow business fields like `model_name` without triggering Pydantic's
    # protected namespace warning under v2.
    model_config = ConfigDict(use_enum_values=True, protected_namespaces=())


class PaginationQuery(APIModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class OperatorPayload(APIModel):
    operator: str = Field(min_length=1)


class TimeRangeQuery(APIModel):
    start_time: datetime | None = None
    end_time: datetime | None = None


class GenericMessage(APIModel):
    detail: str


JSONDict = dict[str, Any]
