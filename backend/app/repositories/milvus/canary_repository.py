from __future__ import annotations

import json
import os
from copy import deepcopy
from threading import Lock
from typing import Any

from pymilvus import Collection, connections, db, utility

from app.repositories.base import CanaryRepository

DEFAULT_MILVUS_ALIAS = "default"
DEFAULT_MILVUS_DB_NAME = "Canary"
VECTOR_DIM = int(os.getenv("MILVUS_VECTOR_DIM", "384"))
REQUIRED_COLLECTIONS = (
    "applications",
    "model_versions",
    "experiments",
    "request_traces",
    "rollback_logs",
    "approval_logs",
)


class MilvusCanaryRepository(CanaryRepository):
    """基于 Milvus collection 的仓储实现。

    V1 重点是把治理数据真正落到 Milvus。复杂的聚合仍放在服务层完成。
    """

    _connected = False
    _lock = Lock()

    def __init__(self) -> None:
        self.host = os.getenv("MILVUS_HOST", "127.0.0.1")
        self.port = os.getenv("MILVUS_PORT", "19530")
        self.alias = os.getenv("MILVUS_ALIAS", DEFAULT_MILVUS_ALIAS)
        self.db_name = os.getenv("MILVUS_DB_NAME", DEFAULT_MILVUS_DB_NAME)
        self._vector_dim_cache: dict[tuple[str, str], int] = {}
        self._connect_once()

    def create_application(self, application: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_application(application)
        self._upsert("applications", payload)
        return deepcopy(application)

    def get_application(self, app_id: str) -> dict[str, Any] | None:
        entity = self._get_by_id("applications", "app_id", app_id)
        return self._denormalize_application(entity) if entity else None

    def get_application_by_name(self, app_name: str) -> dict[str, Any] | None:
        rows = self._query("applications", expr=f'app_name == "{self._escape(app_name)}"', limit=1)
        return self._denormalize_application(rows[0]) if rows else None

    def list_applications(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self._query("applications", expr=self._build_expr(filters, ("owner", "app_type", "status")))
        return [self._denormalize_application(row) for row in rows]

    def update_application(self, app_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get_application(app_id)
        assert current is not None
        current.update(deepcopy(updates))
        return self.create_application(current)

    def create_version(self, version: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_version(version)
        self._upsert("model_versions", payload)
        return deepcopy(version)

    def get_version(self, version_id: str) -> dict[str, Any] | None:
        entity = self._get_by_id("model_versions", "version_id", version_id)
        return self._denormalize_version(entity) if entity else None

    def list_versions(self, app_id: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        expr = self._build_expr({"app_id": app_id, **filters}, ("app_id", "status"))
        rows = self._query("model_versions", expr=expr)
        return [self._denormalize_version(row) for row in rows]

    def update_version(self, version_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get_version(version_id)
        assert current is not None
        current.update(deepcopy(updates))
        return self.create_version(current)

    def create_experiment(self, experiment: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_experiment(experiment)
        self._upsert("experiments", payload)
        return deepcopy(experiment)

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        entity = self._get_by_id("experiments", "experiment_id", experiment_id)
        return self._denormalize_experiment(entity) if entity else None

    def list_experiments(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self._query("experiments", expr=self._build_expr(filters, ("app_id", "status")))
        return [self._denormalize_experiment(row) for row in rows]

    def update_experiment(self, experiment_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get_experiment(experiment_id)
        assert current is not None
        current.update(deepcopy(updates))
        return self.create_experiment(current)

    def list_running_experiments(self, app_id: str) -> list[dict[str, Any]]:
        rows = self._query("experiments", expr=f'app_id == "{self._escape(app_id)}" and status == "running"')
        return [self._denormalize_experiment(row) for row in rows]

    def create_request_trace(self, trace: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_request_trace(trace)
        self._upsert("request_traces", payload)
        return deepcopy(trace)

    def get_request_trace(self, request_id: str) -> dict[str, Any] | None:
        entity = self._get_by_id("request_traces", "request_id", request_id)
        return self._denormalize_request_trace(entity) if entity else None

    def list_request_traces(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self._query(
            "request_traces",
            expr=self._build_expr(filters, ("app_id", "experiment_id", "version_id", "status")),
        )
        items = [self._denormalize_request_trace(row) for row in rows]
        start_time = filters.get("start_time")
        end_time = filters.get("end_time")
        if start_time:
            items = [item for item in items if item["_created_at_dt"] >= start_time]
        if end_time:
            items = [item for item in items if item["_created_at_dt"] <= end_time]
        for item in items:
            item.pop("_created_at_dt", None)
        return items

    def set_decision(self, experiment_id: str, decision: dict[str, Any]) -> dict[str, Any]:
        experiment = self.get_experiment(experiment_id)
        assert experiment is not None
        experiment["last_decision"] = deepcopy(decision)
        self.create_experiment(experiment)
        return deepcopy(decision)

    def get_decision(self, experiment_id: str) -> dict[str, Any] | None:
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            return None
        return deepcopy(experiment.get("last_decision"))

    def append_rollback_log(self, experiment_id: str, rollback_log: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_rollback_log(rollback_log)
        self._upsert("rollback_logs", payload)
        return deepcopy(rollback_log)

    def list_rollback_logs(self, experiment_id: str) -> list[dict[str, Any]]:
        rows = self._query("rollback_logs", expr=f'experiment_id == "{self._escape(experiment_id)}"')
        return [self._denormalize_rollback_log(row) for row in rows]

    def append_approval_log(self, experiment_id: str, approval_log: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_approval_log(approval_log)
        self._upsert("approval_logs", payload)
        return deepcopy(approval_log)

    def list_approval_logs(self, experiment_id: str) -> list[dict[str, Any]]:
        rows = self._query("approval_logs", expr=f'experiment_id == "{self._escape(experiment_id)}"')
        return [self._denormalize_approval_log(row) for row in rows]

    def reset(self) -> None:
        for collection_name in (
            "applications",
            "model_versions",
            "experiments",
            "request_traces",
            "rollback_logs",
            "approval_logs",
        ):
            collection = self._collection(collection_name)
            collection.delete(expr="")

    def _connect_once(self) -> None:
        with self._lock:
            if self.__class__._connected:
                return
            connections.connect(alias=self.alias, host=self.host, port=self.port)
            existing = set(db.list_database(using=self.alias))
            if self.db_name not in existing:
                raise RuntimeError(f"Milvus database '{self.db_name}' does not exist. Run scripts/init_milvus_canary.py first.")
            db.using_database(self.db_name, using=self.alias)
            for collection_name in REQUIRED_COLLECTIONS:
                if not utility.has_collection(collection_name, using=self.alias):
                    raise RuntimeError(f"Milvus collection '{collection_name}' does not exist. Run scripts/init_milvus_canary.py first.")
            self.__class__._connected = True

    def _collection(self, name: str) -> Collection:
        collection = Collection(name=name, using=self.alias)
        collection.load()
        return collection

    def _get_by_id(self, collection_name: str, field_name: str, field_value: str) -> dict[str, Any] | None:
        rows = self._query(collection_name, expr=f'{field_name} == "{self._escape(field_value)}"', limit=1)
        return rows[0] if rows else None

    def _query(self, collection_name: str, expr: str | None = None, limit: int = 10_000) -> list[dict[str, Any]]:
        collection = self._collection(collection_name)
        return collection.query(expr=expr or "", output_fields=["*"], limit=limit)

    def _upsert(self, collection_name: str, payload: dict[str, Any]) -> None:
        collection = self._collection(collection_name)
        collection.upsert([payload])
        collection.flush()

    def _build_expr(self, filters: dict[str, Any], fields: tuple[str, ...]) -> str:
        parts: list[str] = []
        for field_name in fields:
            value = filters.get(field_name)
            if value is None:
                continue
            if isinstance(value, str):
                parts.append(f'{field_name} == "{self._escape(value)}"')
            else:
                parts.append(f"{field_name} == {value}")
        return " and ".join(parts)

    def _normalize_application(self, application: dict[str, Any]) -> dict[str, Any]:
        payload = deepcopy(application)
        payload["description"] = self._none_to_empty_string(payload.get("description"))
        payload["business_scene"] = self._none_to_empty_string(payload.get("business_scene"))
        payload["stable_version_id"] = self._none_to_empty_string(payload.get("stable_version_id"))
        payload["created_at"] = self._to_millis(payload["created_at"])
        payload["updated_at"] = self._to_millis(payload["updated_at"])
        payload["meta_embedding"] = self._zero_vector("applications", "meta_embedding")
        return payload

    def _denormalize_application(self, entity: dict[str, Any]) -> dict[str, Any]:
        item = deepcopy(entity)
        item["description"] = self._empty_string_to_none(item.get("description"))
        item["business_scene"] = self._empty_string_to_none(item.get("business_scene"))
        item["stable_version_id"] = self._empty_string_to_none(item.get("stable_version_id"))
        item["created_at"] = self._from_millis(item["created_at"])
        item["updated_at"] = self._from_millis(item["updated_at"])
        item.pop("meta_embedding", None)
        return item

    def _normalize_version(self, version: dict[str, Any]) -> dict[str, Any]:
        payload = deepcopy(version)
        payload["base_version_id"] = self._none_to_empty_string(payload.get("base_version_id"))
        payload["rag_config_json"] = json.dumps(payload.pop("rag_config", {}), ensure_ascii=False)
        payload["output_schema_json"] = json.dumps(payload.pop("output_schema", {}), ensure_ascii=False)
        payload["created_at"] = self._to_millis(payload["created_at"])
        payload["updated_at"] = self._to_millis(payload["updated_at"])
        payload["config_embedding"] = self._zero_vector("model_versions", "config_embedding")
        return payload

    def _denormalize_version(self, entity: dict[str, Any]) -> dict[str, Any]:
        item = deepcopy(entity)
        item["base_version_id"] = self._empty_string_to_none(item.get("base_version_id"))
        item["rag_config"] = json.loads(item.pop("rag_config_json") or "{}")
        item["output_schema"] = json.loads(item.pop("output_schema_json") or "{}")
        item["created_at"] = self._from_millis(item["created_at"])
        item["updated_at"] = self._from_millis(item["updated_at"])
        item.pop("config_embedding", None)
        return item

    def _normalize_experiment(self, experiment: dict[str, Any]) -> dict[str, Any]:
        payload = deepcopy(experiment)
        payload["stop_reason"] = self._none_to_empty_string(payload.get("stop_reason"))
        payload["routing_rules_json"] = json.dumps(payload.pop("routing_rules", {}), ensure_ascii=False)
        payload["guardrails_json"] = json.dumps(payload.pop("guardrails", {}), ensure_ascii=False)
        payload["last_decision_json"] = json.dumps(payload.pop("last_decision", None), ensure_ascii=False)
        payload["start_time"] = self._optional_to_millis(payload.get("start_time"))
        payload["end_time"] = self._optional_to_millis(payload.get("end_time"))
        payload["created_at"] = self._to_millis(payload["created_at"])
        payload["updated_at"] = self._optional_to_millis(payload.get("updated_at")) or payload["created_at"]
        payload["started_at"] = self._optional_to_millis(payload.get("started_at"))
        payload["stopped_at"] = self._optional_to_millis(payload.get("stopped_at"))
        payload["meta_embedding"] = self._zero_vector("experiments", "meta_embedding")
        return payload

    def _denormalize_experiment(self, entity: dict[str, Any]) -> dict[str, Any]:
        item = deepcopy(entity)
        item["stop_reason"] = self._empty_string_to_none(item.get("stop_reason"))
        item["routing_rules"] = json.loads(item.pop("routing_rules_json") or "{}")
        item["guardrails"] = json.loads(item.pop("guardrails_json") or "{}")
        last_decision_json = item.pop("last_decision_json", None)
        item["last_decision"] = json.loads(last_decision_json) if last_decision_json not in (None, "null", "") else None
        item["start_time"] = self._optional_from_millis(item.get("start_time"))
        item["end_time"] = self._optional_from_millis(item.get("end_time"))
        item["created_at"] = self._from_millis(item["created_at"])
        item["updated_at"] = self._optional_from_millis(item.get("updated_at")) or item["created_at"]
        item["started_at"] = self._optional_from_millis(item.get("started_at"))
        item["stopped_at"] = self._optional_from_millis(item.get("stopped_at"))
        item.pop("meta_embedding", None)
        return item

    def _normalize_request_trace(self, trace: dict[str, Any]) -> dict[str, Any]:
        payload = deepcopy(trace)
        payload["experiment_id"] = self._none_to_empty_string(payload.get("experiment_id"))
        payload["session_id"] = self._none_to_empty_string(payload.get("session_id"))
        payload["error_message"] = self._none_to_empty_string(payload.get("error_message"))
        payload["query_text"] = payload.pop("query")
        payload["answer_text"] = payload.pop("answer") or ""
        payload["retrieval_docs_json"] = json.dumps(payload.pop("retrieval_docs", []), ensure_ascii=False)
        payload["created_at"] = self._to_millis(payload["created_at"])
        payload["query_embedding"] = self._zero_vector("request_traces", "query_embedding")
        return payload

    def _denormalize_request_trace(self, entity: dict[str, Any]) -> dict[str, Any]:
        item = deepcopy(entity)
        item["experiment_id"] = self._empty_string_to_none(item.get("experiment_id"))
        item["session_id"] = self._empty_string_to_none(item.get("session_id"))
        item["error_message"] = self._empty_string_to_none(item.get("error_message"))
        item["query"] = item.pop("query_text")
        item["answer"] = item.pop("answer_text")
        item["retrieval_docs"] = json.loads(item.pop("retrieval_docs_json") or "[]")
        created_at = self._from_millis(item["created_at"])
        item["created_at"] = created_at
        item["_created_at_dt"] = self._parse_dt(created_at)
        item.pop("query_embedding", None)
        return item

    def _normalize_rollback_log(self, rollback_log: dict[str, Any]) -> dict[str, Any]:
        payload = deepcopy(rollback_log)
        payload["trigger_rule"] = self._none_to_empty_string(payload.get("trigger_rule"))
        payload["created_at"] = self._to_millis(payload["created_at"])
        payload["meta_embedding"] = self._zero_vector("rollback_logs", "meta_embedding")
        return payload

    def _denormalize_rollback_log(self, entity: dict[str, Any]) -> dict[str, Any]:
        item = deepcopy(entity)
        item["trigger_rule"] = self._empty_string_to_none(item.get("trigger_rule"))
        item["created_at"] = self._from_millis(item["created_at"])
        item.pop("meta_embedding", None)
        return item

    def _normalize_approval_log(self, approval_log: dict[str, Any]) -> dict[str, Any]:
        payload = deepcopy(approval_log)
        payload["approval_reason"] = self._none_to_empty_string(payload.get("approval_reason"))
        payload["created_at"] = self._to_millis(payload["created_at"])
        payload["meta_embedding"] = self._zero_vector("approval_logs", "meta_embedding")
        return payload

    def _denormalize_approval_log(self, entity: dict[str, Any]) -> dict[str, Any]:
        item = deepcopy(entity)
        item["approval_reason"] = self._empty_string_to_none(item.get("approval_reason"))
        item["created_at"] = self._from_millis(item["created_at"])
        item.pop("meta_embedding", None)
        return item

    def _to_millis(self, value: str) -> int:
        return int(self._parse_dt(value).timestamp() * 1000)

    def _optional_to_millis(self, value: str | None) -> int:
        if not value:
            return 0
        return self._to_millis(value)

    def _from_millis(self, value: int) -> str:
        return self._parse_dt_from_millis(value).isoformat().replace("+00:00", "Z")

    def _optional_from_millis(self, value: int | None) -> str | None:
        if not value:
            return None
        return self._from_millis(value)

    def _parse_dt(self, value: str):
        from datetime import datetime

        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _parse_dt_from_millis(self, value: int):
        from datetime import datetime, timezone

        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)

    def _zero_vector(self, collection_name: str, field_name: str) -> list[float]:
        return [0.0] * self._vector_dim(collection_name, field_name)

    def _vector_dim(self, collection_name: str, field_name: str) -> int:
        cache_key = (collection_name, field_name)
        if cache_key in self._vector_dim_cache:
            return self._vector_dim_cache[cache_key]

        collection = self._collection(collection_name)
        for field in collection.schema.fields:
            if field.name == field_name:
                dim = int(field.params["dim"])
                self._vector_dim_cache[cache_key] = dim
                return dim

        self._vector_dim_cache[cache_key] = VECTOR_DIM
        return VECTOR_DIM

    def _escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _none_to_empty_string(self, value: str | None) -> str:
        return "" if value is None else value

    def _empty_string_to_none(self, value: str | None) -> str | None:
        if value == "":
            return None
        return value
