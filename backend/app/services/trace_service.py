from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.exceptions import AppError
from app.core.repository_provider import get_repository
from app.services.app_service import paginate


class TraceService:
    def create_trace(self, trace: dict[str, Any]) -> None:
        get_repository().create_request_trace(trace)

    def get_request(self, request_id: str) -> dict[str, Any]:
        trace = get_repository().get_request_trace(request_id)
        if not trace:
            raise AppError("request not found", code=40405, status_code=404)
        return trace

    def list_requests(self, filters: dict[str, Any]) -> dict[str, Any]:
        items = get_repository().list_request_traces(filters)
        items.sort(key=lambda item: item["created_at"], reverse=True)
        return paginate(items, filters["page"], filters["page_size"])
