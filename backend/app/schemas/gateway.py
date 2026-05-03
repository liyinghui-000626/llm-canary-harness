from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import APIModel


class GatewayInvokeRequest(APIModel):
    app_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    session_id: str | None = None
    query: str = Field(min_length=1)
    metadata: dict[str, Any] | None = None

