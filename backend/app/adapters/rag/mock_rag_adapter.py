from __future__ import annotations


class MockRAGAdapter:
    """RAG 预留扩展点，V1 先返回固定检索结果。"""

    def retrieve(self, query: str, rag_config: dict) -> list[str]:
        if not rag_config:
            return []
        top_k = rag_config.get("top_k", 2)
        return [f"doc_{index:03d}" for index in range(1, min(top_k, 3) + 1)]

