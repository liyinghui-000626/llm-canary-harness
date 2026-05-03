from __future__ import annotations

from typing import Any


class MockLLMAdapter:
    """V1 默认走 mock 调用，保证接口联调和网关链路可用。"""

    def invoke(self, version: dict[str, Any], query: str, retrieval_docs: list[str]) -> dict[str, Any]:
        if "force_error" in query.lower():
            raise RuntimeError("mock llm forced error")

        answer = f"[{version['model_name']}] 已处理问题：{query}"
        if retrieval_docs:
            answer += f"；参考知识片段 {', '.join(retrieval_docs)}"

        input_tokens = max(32, len(query) * 4 + len(version["prompt_template"]) // 2)
        output_tokens = max(64, min(version["max_tokens"], len(answer) * 2))
        total_tokens = input_tokens + output_tokens
        latency_ms = 800 + min(2200, total_tokens)
        cost = round(total_tokens / 500_000, 6)
        return {
            "answer": answer,
            "model_name": version["model_name"],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "latency_ms": latency_ms,
            "cost": cost,
        }

