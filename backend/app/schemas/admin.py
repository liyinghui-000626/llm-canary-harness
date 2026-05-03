from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator

from app.schemas.common import APIModel


class CreateAppRequest(APIModel):
    app_name: str = Field(min_length=1)
    app_type: str = Field(min_length=1)
    description: str | None = None
    owner: str = Field(min_length=1)
    business_scene: str | None = None


class ListAppsQuery(APIModel):
    owner: str | None = None
    app_type: str | None = None
    status: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class RAGConfig(APIModel):
    vector_db: str | None = None
    top_k: int | None = Field(default=None, ge=1)
    reranker_enabled: bool = False
    reranker_model: str | None = None


class CreateVersionRequest(APIModel):
    version_name: str = Field(min_length=1)
    base_version_id: str | None = None
    prompt_template: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    endpoint_url: str = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=1.0, gt=0, le=1)
    max_tokens: int = Field(default=1024, ge=1)
    rag_enabled: bool
    rag_config: RAGConfig | None = None
    output_schema: dict[str, Any] | None = None
    created_by: str = Field(min_length=1)

    @field_validator("endpoint_url")
    @classmethod
    def validate_endpoint_url(cls, value: str) -> str:
        if value.startswith("mock://"):
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("endpoint_url must be a valid http(s) url or mock:// url")
        return value


class UpdateVersionRequest(APIModel):
    version_name: str = Field(min_length=1)
    base_version_id: str | None = None
    prompt_template: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    endpoint_url: str = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=1.0, gt=0, le=1)
    max_tokens: int = Field(default=1024, ge=1)
    rag_enabled: bool
    rag_config: RAGConfig | None = None
    output_schema: dict[str, Any] | None = None

    @field_validator("endpoint_url")
    @classmethod
    def validate_endpoint_url(cls, value: str) -> str:
        if value.startswith("mock://"):
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("endpoint_url must be a valid http(s) url or mock:// url")
        return value


class ListVersionsQuery(APIModel):
    status: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class SetStableVersionRequest(APIModel):
    version_id: str = Field(min_length=1)
    operator: str = Field(min_length=1)


class SetVersionStatusRequest(APIModel):
    status: Literal["stable", "draft"]
    operator: str = Field(min_length=1)


class RoutingRules(APIModel):
    hash_key: Literal["user_id"] = "user_id"
    whitelist_user_ids: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)


class Guardrails(APIModel):
    max_error_rate: float = Field(ge=0, le=1)
    max_latency_ratio: float = Field(gt=0)
    min_sample_size: int = Field(ge=1)


class CreateExperimentRequest(APIModel):
    app_id: str = Field(min_length=1)
    experiment_name: str = Field(min_length=1)
    control_version_id: str = Field(min_length=1)
    treatment_version_id: str = Field(min_length=1)
    traffic_control: int = Field(ge=0, le=100)
    traffic_treatment: int = Field(ge=0, le=100)
    routing_rules: RoutingRules
    guardrails: Guardrails
    auto_rollback: bool
    start_time: datetime | None = None
    end_time: datetime | None = None
    created_by: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_traffic(self) -> "CreateExperimentRequest":
        if self.traffic_control + self.traffic_treatment != 100:
            raise ValueError("traffic_control + traffic_treatment must equal 100")
        if self.control_version_id == self.treatment_version_id:
            raise ValueError("control_version_id and treatment_version_id must be different")
        return self


class UpdateExperimentRequest(APIModel):
    experiment_name: str = Field(min_length=1)
    control_version_id: str = Field(min_length=1)
    treatment_version_id: str = Field(min_length=1)
    traffic_control: int = Field(ge=0, le=100)
    traffic_treatment: int = Field(ge=0, le=100)
    routing_rules: RoutingRules
    guardrails: Guardrails
    auto_rollback: bool

    @model_validator(mode="after")
    def validate_traffic(self) -> "UpdateExperimentRequest":
        if self.traffic_control + self.traffic_treatment != 100:
            raise ValueError("traffic_control + traffic_treatment must equal 100")
        if self.control_version_id == self.treatment_version_id:
            raise ValueError("control_version_id and treatment_version_id must be different")
        return self


class StopExperimentRequest(APIModel):
    operator: str = Field(min_length=1)
    reason: str | None = None


class ListExperimentsQuery(APIModel):
    app_id: str | None = None
    status: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class ListRequestsQuery(APIModel):
    app_id: str | None = None
    experiment_id: str | None = None
    version_id: str | None = None
    status: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class ExperimentMetricsQuery(APIModel):
    start_time: datetime | None = None
    end_time: datetime | None = None
    interval: str = "5m"


class TimeseriesMetricsQuery(APIModel):
    metric: Literal["error_rate", "avg_latency_ms", "request_count", "avg_cost"]
    interval: str
    start_time: datetime
    end_time: datetime


class RollbackRequest(APIModel):
    operator: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ApproveExpandRequest(APIModel):
    operator: str = Field(min_length=1)
    approved: bool
    approved_split: dict[str, int] | None = None
    approval_reason: str | None = None

    @model_validator(mode="after")
    def validate_split(self) -> "ApproveExpandRequest":
        if self.approved:
            if not self.approved_split:
                raise ValueError("approved_split is required when approved is true")
            control = self.approved_split.get("control")
            treatment = self.approved_split.get("treatment")
            if control is None or treatment is None or control + treatment != 100:
                raise ValueError("approved_split.control + approved_split.treatment must equal 100")
        return self
