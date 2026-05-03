from __future__ import annotations

from app.adapters.llm.http_rag_adapter import HTTPRAGAdapter
from app.services.invoke_service import InvokeService


def test_http_rag_result_does_not_fallback_to_mock_retrieval_docs(monkeypatch) -> None:
    service = InvokeService()

    monkeypatch.setattr(
        service.http_rag_adapter,
        "invoke",
        lambda version, payload: {
            "answer": "real answer",
            "model_name": version["model_name"],
            "retrieval_docs": [],
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
            "latency_ms": 120,
            "cost": 0.0,
        },
    )

    result = service._invoke_http_version(
        {
            "model_name": "real-rag",
            "endpoint_url": "http://127.0.0.1:8000/api/chat",
            "rag_enabled": True,
            "rag_config": {"top_k": 4},
        },
        {
            "app_id": "app_test",
            "user_id": "user-001",
            "query": "hello",
        },
    )

    assert result["retrieval_docs"] == []


def test_http_rag_adapter_builds_message_with_prompt_template() -> None:
    adapter = HTTPRAGAdapter()

    message = adapter._build_message("最近肚子疼", "已经疼了两天")

    assert message == "最近肚子疼"


def test_http_rag_adapter_falls_back_to_query_without_prompt_template() -> None:
    adapter = HTTPRAGAdapter()

    message = adapter._build_message("", "已经疼了两天")

    assert message == "已经疼了两天"
