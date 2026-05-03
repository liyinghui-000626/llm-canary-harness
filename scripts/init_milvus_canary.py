from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Iterable

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    db,
    utility,
)


MILVUS_HOST = os.getenv("MILVUS_HOST", "127.0.0.1")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_ALIAS = os.getenv("MILVUS_ALIAS", "default")
MILVUS_DB_NAME = os.getenv("MILVUS_DB_NAME", "Canary")
VECTOR_DIM = int(os.getenv("MILVUS_VECTOR_DIM", "384"))


@dataclass(frozen=True)
class CollectionDefinition:
    name: str
    schema: CollectionSchema
    vector_fields: tuple[str, ...] = ()


def varchar_field(name: str, max_length: int = 2048, *, is_primary: bool = False) -> FieldSchema:
    return FieldSchema(
        name=name,
        dtype=DataType.VARCHAR,
        max_length=max_length,
        is_primary=is_primary,
        auto_id=False if is_primary else False,
    )


def int64_field(name: str) -> FieldSchema:
    return FieldSchema(name=name, dtype=DataType.INT64)


def float_field(name: str) -> FieldSchema:
    return FieldSchema(name=name, dtype=DataType.FLOAT)


def bool_field(name: str) -> FieldSchema:
    return FieldSchema(name=name, dtype=DataType.BOOL)


def vector_field(name: str) -> FieldSchema:
    return FieldSchema(name=name, dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM)


def create_definitions() -> list[CollectionDefinition]:
    return [
        CollectionDefinition(
            name="applications",
            schema=CollectionSchema(
                fields=[
                    varchar_field("app_id", 64, is_primary=True),
                    varchar_field("app_name", 256),
                    varchar_field("app_type", 64),
                    varchar_field("description", 2048),
                    varchar_field("owner", 128),
                    varchar_field("stable_version_id", 64),
                    varchar_field("status", 32),
                    int64_field("created_at"),
                    int64_field("updated_at"),
                    vector_field("meta_embedding"),
                ],
                description="LLM Canary V1 applications",
                enable_dynamic_field=True,
            ),
            vector_fields=("meta_embedding",),
        ),
        CollectionDefinition(
            name="model_versions",
            schema=CollectionSchema(
                fields=[
                    varchar_field("version_id", 64, is_primary=True),
                    varchar_field("app_id", 64),
                    varchar_field("version_name", 256),
                    varchar_field("base_version_id", 64),
                    varchar_field("prompt_template", 8192),
                    varchar_field("model_name", 256),
                    varchar_field("endpoint_url", 512),
                    float_field("temperature"),
                    float_field("top_p"),
                    int64_field("max_tokens"),
                    bool_field("rag_enabled"),
                    varchar_field("rag_config_json", 8192),
                    varchar_field("output_schema_json", 4096),
                    varchar_field("status", 32),
                    varchar_field("created_by", 128),
                    int64_field("created_at"),
                    int64_field("updated_at"),
                    vector_field("config_embedding"),
                ],
                description="LLM Canary V1 version configurations",
                enable_dynamic_field=True,
            ),
            vector_fields=("config_embedding",),
        ),
        CollectionDefinition(
            name="experiments",
            schema=CollectionSchema(
                fields=[
                    varchar_field("experiment_id", 64, is_primary=True),
                    varchar_field("app_id", 64),
                    varchar_field("experiment_name", 256),
                    varchar_field("control_version_id", 64),
                    varchar_field("treatment_version_id", 64),
                    int64_field("traffic_control"),
                    int64_field("traffic_treatment"),
                    varchar_field("status", 32),
                    bool_field("auto_rollback"),
                    int64_field("start_time"),
                    int64_field("end_time"),
                    varchar_field("created_by", 128),
                    int64_field("created_at"),
                    vector_field("meta_embedding"),
                ],
                description="LLM Canary V1 experiments",
                enable_dynamic_field=True,
            ),
            vector_fields=("meta_embedding",),
        ),
        CollectionDefinition(
            name="routing_rules",
            schema=CollectionSchema(
                fields=[
                    varchar_field("rule_id", 64, is_primary=True),
                    varchar_field("experiment_id", 64),
                    varchar_field("rule_type", 64),
                    int64_field("priority"),
                    bool_field("enabled"),
                    varchar_field("rule_config_json", 4096),
                    int64_field("created_at"),
                    vector_field("meta_embedding"),
                ],
                description="LLM Canary V1 routing rules",
                enable_dynamic_field=True,
            ),
            vector_fields=("meta_embedding",),
        ),
        CollectionDefinition(
            name="request_traces",
            schema=CollectionSchema(
                fields=[
                    varchar_field("request_id", 64, is_primary=True),
                    varchar_field("trace_id", 64),
                    varchar_field("app_id", 64),
                    varchar_field("experiment_id", 64),
                    varchar_field("version_id", 64),
                    varchar_field("user_id", 128),
                    varchar_field("session_id", 128),
                    varchar_field("query_text", 8192),
                    varchar_field("answer_text", 16384),
                    varchar_field("routing_reason", 512),
                    varchar_field("model_name", 256),
                    varchar_field("retrieval_docs_json", 8192),
                    int64_field("input_tokens"),
                    int64_field("output_tokens"),
                    int64_field("total_tokens"),
                    int64_field("latency_ms"),
                    float_field("cost"),
                    varchar_field("status", 32),
                    varchar_field("error_message", 4096),
                    int64_field("created_at"),
                    vector_field("query_embedding"),
                ],
                description="LLM Canary V1 request traces",
                enable_dynamic_field=True,
            ),
            vector_fields=("query_embedding",),
        ),
        CollectionDefinition(
            name="metric_snapshots",
            schema=CollectionSchema(
                fields=[
                    varchar_field("snapshot_id", 64, is_primary=True),
                    varchar_field("app_id", 64),
                    varchar_field("experiment_id", 64),
                    varchar_field("version_id", 64),
                    varchar_field("window_type", 32),
                    int64_field("request_count"),
                    int64_field("success_count"),
                    int64_field("error_count"),
                    float_field("avg_latency_ms"),
                    float_field("p95_latency_ms"),
                    float_field("avg_cost"),
                    int64_field("total_input_tokens"),
                    int64_field("total_output_tokens"),
                    int64_field("generated_at"),
                    vector_field("meta_embedding"),
                ],
                description="LLM Canary V1 metric snapshots",
                enable_dynamic_field=True,
            ),
            vector_fields=("meta_embedding",),
        ),
        CollectionDefinition(
            name="rollback_logs",
            schema=CollectionSchema(
                fields=[
                    varchar_field("rollback_id", 64, is_primary=True),
                    varchar_field("experiment_id", 64),
                    varchar_field("from_version_id", 64),
                    varchar_field("to_version_id", 64),
                    varchar_field("trigger_rule", 128),
                    varchar_field("reason", 2048),
                    varchar_field("operator", 64),
                    varchar_field("status", 32),
                    int64_field("created_at"),
                    vector_field("meta_embedding"),
                ],
                description="LLM Canary V1 rollback logs",
                enable_dynamic_field=True,
            ),
            vector_fields=("meta_embedding",),
        ),
        CollectionDefinition(
            name="approval_logs",
            schema=CollectionSchema(
                fields=[
                    varchar_field("approval_id", 64, is_primary=True),
                    varchar_field("experiment_id", 64),
                    varchar_field("current_split", 32),
                    varchar_field("recommended_split", 32),
                    varchar_field("approved_by", 128),
                    varchar_field("approval_reason", 2048),
                    varchar_field("status", 32),
                    int64_field("created_at"),
                    vector_field("meta_embedding"),
                ],
                description="LLM Canary V1 approval logs",
                enable_dynamic_field=True,
            ),
            vector_fields=("meta_embedding",),
        ),
    ]


def ensure_database() -> None:
    existing = set(db.list_database())
    if MILVUS_DB_NAME not in existing:
        db.create_database(MILVUS_DB_NAME)
        print(f"[created] database={MILVUS_DB_NAME}")
    else:
        print(f"[exists] database={MILVUS_DB_NAME}")
    db.using_database(MILVUS_DB_NAME)


def ensure_collection(definition: CollectionDefinition) -> Collection:
    if utility.has_collection(definition.name, using=MILVUS_ALIAS):
        collection = Collection(name=definition.name, using=MILVUS_ALIAS)
        print(f"[exists] collection={definition.name}")
    else:
        collection = Collection(
            name=definition.name,
            schema=definition.schema,
            using=MILVUS_ALIAS,
            shards_num=2,
        )
        print(f"[created] collection={definition.name}")
    for field_name in definition.vector_fields:
        ensure_vector_index(collection, field_name)
    return collection


def ensure_vector_index(collection: Collection, field_name: str) -> None:
    existing = [idx.field_name for idx in collection.indexes]
    if field_name in existing:
        print(f"[exists] index={collection.name}.{field_name}")
        return

    index_params = {
        "index_type": "IVF_FLAT",
        "metric_type": "COSINE",
        "params": {"nlist": 1024},
    }
    collection.create_index(field_name=field_name, index_params=index_params)
    print(f"[created] index={collection.name}.{field_name}")


def load_collections(definitions: Iterable[CollectionDefinition]) -> None:
    for definition in definitions:
        collection = Collection(name=definition.name, using=MILVUS_ALIAS)
        collection.load()
        print(f"[loaded] collection={definition.name}")


def connect() -> None:
    connections.connect(alias=MILVUS_ALIAS, host=MILVUS_HOST, port=MILVUS_PORT)
    print(f"[connected] {MILVUS_HOST}:{MILVUS_PORT}")


def main() -> None:
    start = time.time()
    connect()
    ensure_database()
    definitions = create_definitions()
    for definition in definitions:
        ensure_collection(definition)
    load_collections(definitions)
    elapsed = round(time.time() - start, 2)
    print(f"[done] database={MILVUS_DB_NAME} collections={len(definitions)} elapsed={elapsed}s")


if __name__ == "__main__":
    main()
