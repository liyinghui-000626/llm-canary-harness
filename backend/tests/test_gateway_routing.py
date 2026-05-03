from __future__ import annotations

from fastapi.testclient import TestClient

from apps.admin_api.main import app as admin_app
from apps.gateway_api.main import app as gateway_app


admin_client = TestClient(admin_app)
gateway_client = TestClient(gateway_app)


def bootstrap_running_experiment() -> tuple[str, str, str]:
    app_response = admin_client.post(
        "/canary/api/v1/apps",
        json={
            "app_name": "routing-bot",
            "app_type": "RAG",
            "description": "分流测试",
            "owner": "alice",
            "business_scene": "customer_support",
        },
    )
    app_id = app_response.json()["data"]["app_id"]

    version_1 = admin_client.post(
        f"/canary/api/v1/apps/{app_id}/versions",
        json={
            "version_name": "control",
            "base_version_id": None,
            "prompt_template": "control prompt",
            "model_name": "model-control",
            "endpoint_url": "mock://llm",
            "temperature": 0.2,
            "top_p": 0.9,
            "max_tokens": 512,
            "rag_enabled": False,
            "rag_config": {},
            "output_schema": {},
            "created_by": "alice",
        },
    ).json()["data"]["version_id"]
    version_2 = admin_client.post(
        f"/canary/api/v1/apps/{app_id}/versions",
        json={
            "version_name": "treatment",
            "base_version_id": version_1,
            "prompt_template": "treatment prompt",
            "model_name": "model-treatment",
            "endpoint_url": "mock://llm",
            "temperature": 0.2,
            "top_p": 0.9,
            "max_tokens": 512,
            "rag_enabled": True,
            "rag_config": {"top_k": 2},
            "output_schema": {},
            "created_by": "alice",
        },
    ).json()["data"]["version_id"]

    admin_client.post(
        f"/canary/api/v1/apps/{app_id}/stable-version",
        json={"version_id": version_1, "operator": "alice"},
    )
    experiment_id = admin_client.post(
        "/canary/api/v1/experiments",
        json={
            "app_id": app_id,
            "experiment_name": "routing-canary",
            "control_version_id": version_1,
            "treatment_version_id": version_2,
            "traffic_control": 90,
            "traffic_treatment": 10,
            "routing_rules": {"hash_key": "user_id", "whitelist_user_ids": ["vip-user"], "channels": []},
            "guardrails": {"max_error_rate": 0.5, "max_latency_ratio": 2.0, "min_sample_size": 10},
            "auto_rollback": True,
            "created_by": "alice",
        },
    ).json()["data"]["experiment_id"]
    admin_client.post(f"/canary/api/v1/experiments/{experiment_id}/start", json={"operator": "alice"})
    return app_id, version_1, version_2


def test_gateway_routing_is_stable_for_same_user() -> None:
    app_id, _, _ = bootstrap_running_experiment()

    first = gateway_client.post(
        "/canary/api/v1/gateway/invoke",
        json={
            "app_id": app_id,
            "user_id": "same-user-001",
            "session_id": "sess-1",
            "query": "我的订单什么时候发货？",
            "metadata": {"channel": "web"},
        },
    )
    second = gateway_client.post(
        "/canary/api/v1/gateway/invoke",
        json={
            "app_id": app_id,
            "user_id": "same-user-001",
            "session_id": "sess-2",
            "query": "再问一次发货时间",
            "metadata": {"channel": "web"},
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["version_id"] == second.json()["data"]["version_id"]
    assert first.json()["data"]["routing_reason"] == second.json()["data"]["routing_reason"]


def test_gateway_whitelist_hits_treatment_and_trace_recorded() -> None:
    app_id, _, treatment_version_id = bootstrap_running_experiment()

    response = gateway_client.post(
        "/canary/api/v1/gateway/invoke",
        json={
            "app_id": app_id,
            "user_id": "vip-user",
            "session_id": "sess-whitelist",
            "query": "帮我查一下售后政策",
            "metadata": {"channel": "web"},
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["version_id"] == treatment_version_id
    assert payload["routing_reason"] == "whitelist_hit_treatment"
    assert payload["status"] == "success"

    trace_response = admin_client.get(f"/canary/api/v1/requests/{payload['request_id']}")
    assert trace_response.status_code == 200
    trace = trace_response.json()["data"]
    assert trace["version_id"] == treatment_version_id
    assert trace["routing_reason"] == "whitelist_hit_treatment"
    assert trace["retrieval_docs"] == ["doc_001", "doc_002"]
