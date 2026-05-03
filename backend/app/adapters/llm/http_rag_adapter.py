from __future__ import annotations

import os
from time import perf_counter
from typing import Any
from urllib.parse import urlparse

import httpx


class HTTPRAGAdapter:
    """调用外部 HTTP RAG 应用。

    当前接入目标是一个 FastAPI 健康助手服务：
    - 默认聊天入口: POST /api/chat
    - 请求体: {"user_id": "...", "message": "..."}
    - 返回体: {"answer": "...", "sources": [...], "model": "...", "trace": [...]}

    `endpoint_url` 既可以直接填完整聊天接口 URL，
    也可以只填服务根地址，例如 `http://127.0.0.1:8000`。
    """

    def __init__(self) -> None:
        self.timeout = float(os.getenv("CANARY_HTTP_RAG_TIMEOUT_SECONDS", "90"))

    def invoke(self, version: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        target_url = self._resolve_target_url(version["endpoint_url"])
        prompt_template = str(version.get("prompt_template") or "").strip()
        query = str(payload["query"]).strip()
        message = self._build_message(prompt_template, query)
        request_body = {
            "user_id": payload["user_id"],
            "message": message,
        }

        started_at = perf_counter()
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(target_url, json=request_body)
        latency_ms = max(1, int((perf_counter() - started_at) * 1000))

        response.raise_for_status()
        raw_payload = response.json()
        result = self._unwrap_payload(raw_payload)

        answer = result.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError(f"unexpected RAG response payload: {raw_payload}")

        sources = result.get("sources") or []
        if not isinstance(sources, list):
            sources = []

        model_name = result.get("model") or version["model_name"]
        if not isinstance(model_name, str) or not model_name:
            model_name = version["model_name"]

        usage_log = self._fetch_latest_usage(
            endpoint_url=version["endpoint_url"],
            user_id=payload["user_id"],
            question=message,
        )

        prompt_tokens = int((usage_log or {}).get("prompt_tokens") or 0)
        completion_tokens = int((usage_log or {}).get("completion_tokens") or 0)
        total_tokens = int((usage_log or {}).get("total_tokens") or (prompt_tokens + completion_tokens))
        usage_sources = (((usage_log or {}).get("metadata") or {}).get("sources")) or []
        if not sources and isinstance(usage_sources, list):
            sources = usage_sources

        return {
            "answer": answer,
            "model_name": model_name,
            "retrieval_docs": [str(item) for item in sources],
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "latency_ms": latency_ms,
            "cost": 0.0,
        }

    def _build_message(self, prompt_template: str, query: str) -> str:
        if not prompt_template:
            return query
        return prompt_template

    def _resolve_target_url(self, endpoint_url: str) -> str:
        parsed = urlparse(endpoint_url)
        if parsed.scheme not in {"http", "https"}:
            raise RuntimeError(f"unsupported endpoint_url for HTTPRAGAdapter: {endpoint_url}")

        if parsed.path and parsed.path not in {"", "/"}:
            return endpoint_url
        return endpoint_url.rstrip("/") + "/api/chat"

    def _unwrap_payload(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RuntimeError(f"unexpected non-object RAG response: {payload!r}")

        # 兼容直接返回 ChatResponse，以及少数接口会包一层 {"message", "data"} 的情况。
        if "answer" in payload:
            return payload
        nested = payload.get("data")
        if isinstance(nested, dict):
            return nested
        raise RuntimeError(f"unexpected RAG response payload: {payload}")

    def _fetch_latest_usage(self, *, endpoint_url: str, user_id: str, question: str) -> dict[str, Any] | None:
        usage_url = self._resolve_usage_url(endpoint_url, user_id)
        with httpx.Client(timeout=min(self.timeout, 20)) as client:
            response = client.get(usage_url, params={"limit": 10})
        response.raise_for_status()
        payload = response.json()

        rows = []
        if isinstance(payload, dict):
            rows = ((payload.get("data") or {}).get("logs")) or []
        if not isinstance(rows, list):
            return None

        matched = [row for row in rows if isinstance(row, dict) and row.get("question") == question]
        if not matched:
            return None
        matched.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return matched[0]

    def _resolve_usage_url(self, endpoint_url: str, user_id: str) -> str:
        parsed = urlparse(endpoint_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        return f"{origin}/api/llm-usage/{user_id}"
