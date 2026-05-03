from __future__ import annotations

import os
import time
from typing import Any

import httpx


ADMIN_BASE_URL = os.getenv("ADMIN_BASE_URL", "http://127.0.0.1:8000")
GATEWAY_BASE_URL = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8001")
TIMEOUT = float(os.getenv("SMOKE_TEST_TIMEOUT_SECONDS", "20"))


def ensure_ok(response: httpx.Response, expected_status: int) -> dict[str, Any]:
    if response.status_code != expected_status:
        raise AssertionError(
            f"unexpected status={response.status_code} expected={expected_status} body={response.text}"
        )
    payload = response.json()
    if payload["code"] != 0:
        raise AssertionError(f"unexpected business code={payload['code']} body={payload}")
    return payload["data"]


def main() -> int:
    run_suffix = str(int(time.time() * 1000))
    app_name = f"smoke-app-{run_suffix}"
    control_name = f"smoke-control-{run_suffix}"
    treatment_name = f"smoke-treatment-{run_suffix}"
    experiment_name = f"smoke-exp-{run_suffix}"

    with httpx.Client(timeout=TIMEOUT) as client:
        health = client.get(f"{ADMIN_BASE_URL}/canary")
        ensure_ok_wrap(health, 200, expect_json=False)
        health = client.get(f"{GATEWAY_BASE_URL}/canary")
        ensure_ok_wrap(health, 200, expect_json=False)

        app = ensure_ok(
            client.post(
                f"{ADMIN_BASE_URL}/canary/api/v1/apps",
                json={
                    "app_name": app_name,
                    "app_type": "RAG",
                    "description": "smoke test app",
                    "owner": "smoke",
                    "business_scene": "smoke",
                },
            ),
            201,
        )
        app_id = app["app_id"]

        control_version = ensure_ok(
            client.post(
                f"{ADMIN_BASE_URL}/canary/api/v1/apps/{app_id}/versions",
                json={
                    "version_name": control_name,
                    "base_version_id": None,
                    "prompt_template": "control prompt",
                    "model_name": "mock-control",
                    "endpoint_url": "mock://llm",
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "max_tokens": 512,
                    "rag_enabled": False,
                    "rag_config": {},
                    "output_schema": {"type": "markdown"},
                    "created_by": "smoke",
                },
            ),
            201,
        )
        treatment_version = ensure_ok(
            client.post(
                f"{ADMIN_BASE_URL}/canary/api/v1/apps/{app_id}/versions",
                json={
                    "version_name": treatment_name,
                    "base_version_id": control_version["version_id"],
                    "prompt_template": "treatment prompt",
                    "model_name": "mock-treatment",
                    "endpoint_url": "mock://llm",
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "max_tokens": 512,
                    "rag_enabled": True,
                    "rag_config": {"top_k": 2, "reranker_enabled": False},
                    "output_schema": {"type": "markdown"},
                    "created_by": "smoke",
                },
            ),
            201,
        )

        ensure_ok(
            client.post(
                f"{ADMIN_BASE_URL}/canary/api/v1/apps/{app_id}/stable-version",
                json={"version_id": control_version["version_id"], "operator": "smoke"},
            ),
            200,
        )

        experiment = ensure_ok(
            client.post(
                f"{ADMIN_BASE_URL}/canary/api/v1/experiments",
                json={
                    "app_id": app_id,
                    "experiment_name": experiment_name,
                    "control_version_id": control_version["version_id"],
                    "treatment_version_id": treatment_version["version_id"],
                    "traffic_control": 90,
                    "traffic_treatment": 10,
                    "routing_rules": {"hash_key": "user_id", "whitelist_user_ids": ["vip-smoke"], "channels": []},
                    "guardrails": {"max_error_rate": 0.5, "max_latency_ratio": 2.0, "min_sample_size": 1},
                    "auto_rollback": True,
                    "created_by": "smoke",
                },
            ),
            201,
        )
        experiment_id = experiment["experiment_id"]

        started = ensure_ok(
            client.post(
                f"{ADMIN_BASE_URL}/canary/api/v1/experiments/{experiment_id}/start",
                json={"operator": "smoke"},
            ),
            200,
        )
        assert started["status"] == "running"

        first_invoke = ensure_ok(
            client.post(
                f"{GATEWAY_BASE_URL}/canary/api/v1/gateway/invoke",
                json={
                    "app_id": app_id,
                    "user_id": "vip-smoke",
                    "session_id": "smoke-sess-1",
                    "query": "hello canary",
                    "metadata": {"channel": "web"},
                },
            ),
            200,
        )
        assert first_invoke["version_id"] == treatment_version["version_id"]
        assert first_invoke["routing_reason"] == "whitelist_hit_treatment"

        second_invoke = ensure_ok(
            client.post(
                f"{GATEWAY_BASE_URL}/canary/api/v1/gateway/invoke",
                json={
                    "app_id": app_id,
                    "user_id": "stable-user",
                    "session_id": "smoke-sess-2",
                    "query": "hello again",
                    "metadata": {"channel": "web"},
                },
            ),
            200,
        )
        third_invoke = ensure_ok(
            client.post(
                f"{GATEWAY_BASE_URL}/canary/api/v1/gateway/invoke",
                json={
                    "app_id": app_id,
                    "user_id": "stable-user",
                    "session_id": "smoke-sess-3",
                    "query": "hello again 2",
                    "metadata": {"channel": "web"},
                },
            ),
            200,
        )
        assert second_invoke["version_id"] == third_invoke["version_id"]
        assert second_invoke["routing_reason"] == third_invoke["routing_reason"]

        request_trace = ensure_ok(
            client.get(f"{ADMIN_BASE_URL}/canary/api/v1/requests/{first_invoke['request_id']}"),
            200,
        )
        assert request_trace["version_id"] == treatment_version["version_id"]
        assert request_trace["retrieval_docs"] == ["doc_001", "doc_002"]

        metrics = ensure_ok(
            client.get(f"{ADMIN_BASE_URL}/canary/api/v1/experiments/{experiment_id}/metrics"),
            200,
        )
        assert metrics["treatment"]["request_count"] >= 1

        decision = ensure_ok(
            client.post(
                f"{ADMIN_BASE_URL}/canary/api/v1/experiments/{experiment_id}/decision/recompute",
                json={"operator": "smoke"},
            ),
            200,
        )
        assert decision["decision_type"] in {"rollback", "recommend_expand", "keep_observing"}

    print("smoke test passed")
    return 0


def ensure_ok_wrap(response: httpx.Response, expected_status: int, *, expect_json: bool) -> None:
    if response.status_code != expected_status:
        raise AssertionError(
            f"unexpected status={response.status_code} expected={expected_status} body={response.text}"
        )
    if expect_json:
        ensure_ok(response, expected_status)


if __name__ == "__main__":
    raise SystemExit(main())
