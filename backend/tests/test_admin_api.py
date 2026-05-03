from __future__ import annotations

from fastapi.testclient import TestClient

from apps.admin_api.main import app


client = TestClient(app)


def create_app() -> str:
    response = client.post(
        "/canary/api/v1/apps",
        json={
            "app_name": "support-bot",
            "app_type": "RAG",
            "description": "售后问答机器人",
            "owner": "alice",
            "business_scene": "customer_support",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["app_id"]


def create_version(app_id: str, version_name: str, model_name: str) -> str:
    response = client.post(
        f"/canary/api/v1/apps/{app_id}/versions",
        json={
            "version_name": version_name,
            "base_version_id": None,
            "prompt_template": f"prompt for {version_name}",
            "model_name": model_name,
            "endpoint_url": "mock://llm",
            "temperature": 0.2,
            "top_p": 0.8,
            "max_tokens": 512,
            "rag_enabled": version_name == "v2",
            "rag_config": {"top_k": 2},
            "output_schema": {"type": "markdown"},
            "created_by": "alice",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["version_id"]


def test_experiment_status_flow() -> None:
    app_id = create_app()
    control_version_id = create_version(app_id, "v1", "model-a")
    treatment_version_id = create_version(app_id, "v2", "model-b")

    stable_response = client.post(
        f"/canary/api/v1/apps/{app_id}/stable-version",
        json={"version_id": control_version_id, "operator": "alice"},
    )
    assert stable_response.status_code == 200
    assert stable_response.json()["data"]["stable_version_id"] == control_version_id

    create_experiment_response = client.post(
        "/canary/api/v1/experiments",
        json={
            "app_id": app_id,
            "experiment_name": "canary-exp",
            "control_version_id": control_version_id,
            "treatment_version_id": treatment_version_id,
            "traffic_control": 90,
            "traffic_treatment": 10,
            "routing_rules": {"hash_key": "user_id", "whitelist_user_ids": [], "channels": []},
            "guardrails": {"max_error_rate": 0.05, "max_latency_ratio": 1.5, "min_sample_size": 100},
            "auto_rollback": True,
            "created_by": "alice",
        },
    )
    assert create_experiment_response.status_code == 201
    experiment_id = create_experiment_response.json()["data"]["experiment_id"]
    assert create_experiment_response.json()["data"]["status"] == "created"

    start_response = client.post(
        f"/canary/api/v1/experiments/{experiment_id}/start",
        json={"operator": "alice"},
    )
    assert start_response.status_code == 200
    assert start_response.json()["data"]["status"] == "running"

    running_detail = client.get(f"/canary/api/v1/experiments/{experiment_id}")
    assert running_detail.status_code == 200
    assert running_detail.json()["data"]["status"] == "running"
    assert running_detail.json()["data"]["started_at"] is not None

    stop_response = client.post(
        f"/canary/api/v1/experiments/{experiment_id}/stop",
        json={"operator": "alice", "reason": "manual stop"},
    )
    assert stop_response.status_code == 200
    assert stop_response.json()["data"]["status"] == "stopped"

    stopped_detail = client.get(f"/canary/api/v1/experiments/{experiment_id}")
    assert stopped_detail.status_code == 200
    assert stopped_detail.json()["data"]["status"] == "stopped"
    assert stopped_detail.json()["data"]["stop_reason"] == "manual stop"

    restart_response = client.post(
        f"/canary/api/v1/experiments/{experiment_id}/start",
        json={"operator": "alice"},
    )
    assert restart_response.status_code == 200
    assert restart_response.json()["data"]["status"] == "running"

    restarted_detail = client.get(f"/canary/api/v1/experiments/{experiment_id}")
    assert restarted_detail.status_code == 200
    assert restarted_detail.json()["data"]["status"] == "running"
    assert restarted_detail.json()["data"]["started_at"] is not None
    assert restarted_detail.json()["data"]["stopped_at"] is None
    assert restarted_detail.json()["data"]["stop_reason"] is None


def test_update_experiment_detail() -> None:
    app_id = create_app()
    control_version_id = create_version(app_id, "v1", "model-a")
    treatment_version_id = create_version(app_id, "v2", "model-b")

    stable_response = client.post(
        f"/canary/api/v1/apps/{app_id}/stable-version",
        json={"version_id": control_version_id, "operator": "alice"},
    )
    assert stable_response.status_code == 200

    create_experiment_response = client.post(
        "/canary/api/v1/experiments",
        json={
            "app_id": app_id,
            "experiment_name": "editable-exp",
            "control_version_id": control_version_id,
            "treatment_version_id": treatment_version_id,
            "traffic_control": 90,
            "traffic_treatment": 10,
            "routing_rules": {"hash_key": "user_id", "whitelist_user_ids": ["seed-user"], "channels": []},
            "guardrails": {"max_error_rate": 0.05, "max_latency_ratio": 1.5, "min_sample_size": 100},
            "auto_rollback": True,
            "created_by": "alice",
        },
    )
    assert create_experiment_response.status_code == 201
    experiment_id = create_experiment_response.json()["data"]["experiment_id"]

    update_response = client.put(
        f"/canary/api/v1/experiments/{experiment_id}",
        json={
            "experiment_name": "editable-exp-updated",
            "control_version_id": control_version_id,
            "treatment_version_id": treatment_version_id,
            "traffic_control": 85,
            "traffic_treatment": 15,
            "routing_rules": {"hash_key": "user_id", "whitelist_user_ids": ["vip-user", "seed-user"], "channels": []},
            "guardrails": {"max_error_rate": 0.08, "max_latency_ratio": 1.8, "min_sample_size": 300},
            "auto_rollback": False,
        },
    )
    assert update_response.status_code == 200
    payload = update_response.json()["data"]
    assert payload["experiment_name"] == "editable-exp-updated"
    assert payload["traffic_control"] == 85
    assert payload["traffic_treatment"] == 15
    assert payload["guardrails"]["max_error_rate"] == 0.08
    assert payload["guardrails"]["max_latency_ratio"] == 1.8
    assert payload["guardrails"]["min_sample_size"] == 300
    assert payload["routing_rules"]["whitelist_user_ids"] == ["vip-user", "seed-user"]
    assert payload["auto_rollback"] is False

    detail_response = client.get(f"/canary/api/v1/experiments/{experiment_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["experiment_name"] == "editable-exp-updated"
    assert detail["traffic_control"] == 85
    assert detail["traffic_treatment"] == 15
    assert detail["guardrails"]["max_error_rate"] == 0.08
    assert detail["routing_rules"]["whitelist_user_ids"] == ["vip-user", "seed-user"]
    assert detail["auto_rollback"] is False


def test_update_version_and_promote_stable() -> None:
    app_id = create_app()
    version_1 = create_version(app_id, "v1", "model-a")
    version_2 = create_version(app_id, "v2", "model-b")

    update_response = client.put(
        f"/canary/api/v1/versions/{version_2}",
        json={
            "version_name": "v2-updated",
            "base_version_id": version_1,
            "prompt_template": "updated prompt template",
            "model_name": "deepseek-v4-flash",
            "endpoint_url": "mock://llm",
            "temperature": 0.4,
            "top_p": 0.95,
            "max_tokens": 2048,
            "rag_enabled": True,
            "rag_config": {"vector_db": "Milvus", "top_k": 8, "reranker_enabled": False},
            "output_schema": {"type": "markdown"},
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["version_name"] == "v2-updated"
    assert updated["prompt_template"] == "updated prompt template"
    assert updated["model_name"] == "deepseek-v4-flash"
    assert updated["max_tokens"] == 2048
    assert updated["rag_config"]["top_k"] == 8

    stable_response = client.post(
        f"/canary/api/v1/apps/{app_id}/stable-version",
        json={"version_id": version_2, "operator": "alice"},
    )
    assert stable_response.status_code == 200
    assert stable_response.json()["data"]["stable_version_id"] == version_2

    app_detail = client.get(f"/canary/api/v1/apps/{app_id}")
    assert app_detail.status_code == 200
    assert app_detail.json()["data"]["stable_version_id"] == version_2

    version_2_detail = client.get(f"/canary/api/v1/versions/{version_2}")
    assert version_2_detail.status_code == 200
    assert version_2_detail.json()["data"]["status"] == "stable"

    version_1_detail = client.get(f"/canary/api/v1/versions/{version_1}")
    assert version_1_detail.status_code == 200
    assert version_1_detail.json()["data"]["status"] == "draft"


def test_set_version_status_to_draft_clears_stable_version() -> None:
    app_id = create_app()
    version_1 = create_version(app_id, "v1", "model-a")

    stable_response = client.post(
        f"/canary/api/v1/apps/{app_id}/stable-version",
        json={"version_id": version_1, "operator": "alice"},
    )
    assert stable_response.status_code == 200

    demote_response = client.post(
        f"/canary/api/v1/versions/{version_1}/status",
        json={"status": "draft", "operator": "alice"},
    )
    assert demote_response.status_code == 200
    assert demote_response.json()["data"]["status"] == "draft"

    app_detail = client.get(f"/canary/api/v1/apps/{app_id}")
    assert app_detail.status_code == 200
    assert app_detail.json()["data"]["stable_version_id"] is None
