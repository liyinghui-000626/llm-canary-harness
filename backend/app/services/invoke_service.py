from __future__ import annotations

from typing import Any

from app.adapters.llm.http_rag_adapter import HTTPRAGAdapter
from app.adapters.llm.mock_llm_adapter import MockLLMAdapter
from app.adapters.rag.mock_rag_adapter import MockRAGAdapter
from app.domain.enums.status import RequestStatus
from app.services.routing_service import RoutingService
from app.services.trace_service import TraceService
from app.utils.id_utils import id_generator
from app.utils.time_utils import utcnow_iso


class InvokeService:
    def __init__(self) -> None:
        self.routing_service = RoutingService()
        self.trace_service = TraceService()
        self.rag_adapter = MockRAGAdapter()
        self.http_rag_adapter = HTTPRAGAdapter()
        self.llm_adapter = MockLLMAdapter()

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_id = id_generator.next_id("req")
        trace_id = id_generator.next_id("trace")
        route = self.routing_service.resolve_route(payload["app_id"], payload["user_id"], payload.get("metadata"))
        version = route["version"]

        trace = {
            "request_id": request_id,
            "trace_id": trace_id,
            "app_id": payload["app_id"],
            "experiment_id": route["experiment_id"],
            "version_id": route["version_id"],
            "user_id": payload["user_id"],
            "session_id": payload.get("session_id"),
            "query": payload["query"],
            "answer": None,
            "routing_reason": route["routing_reason"],
            "model_name": version["model_name"],
            "retrieval_docs": [],
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "latency_ms": 0,
            "cost": 0,
            "status": RequestStatus.SUCCESS.value,
            "error_message": None,
            "created_at": utcnow_iso(),
        }

        try:
            result = self._invoke_version(version, payload)
            trace.update(result)
            self.trace_service.create_trace(trace)
            return {
                "request_id": request_id,
                "trace_id": trace_id,
                "experiment_id": route["experiment_id"],
                "version_id": route["version_id"],
                "routing_reason": route["routing_reason"],
                **result,
                "status": RequestStatus.SUCCESS.value,
            }
        except Exception as exc:  # noqa: BLE001
            trace["status"] = RequestStatus.ERROR.value
            trace["error_message"] = str(exc)
            self.trace_service.create_trace(trace)
            raise

    def _invoke_version(
        self,
        version: dict[str, Any],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        endpoint_url = version.get("endpoint_url", "")
        if endpoint_url.startswith("mock://"):
            return self._invoke_mock_version(version, payload)
        return self._invoke_http_version(version, payload)

    def _invoke_mock_version(self, version: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        retrieval_docs = self.rag_adapter.retrieve(payload["query"], version.get("rag_config", {})) if version["rag_enabled"] else []
        result = self.llm_adapter.invoke(version, payload["query"], retrieval_docs)
        result["retrieval_docs"] = retrieval_docs
        return result

    def _invoke_http_version(self, version: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        result = self.http_rag_adapter.invoke(version, payload)
        result["retrieval_docs"] = [str(item) for item in result.get("retrieval_docs") or []]
        return result
