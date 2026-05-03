from __future__ import annotations

from fastapi import APIRouter, Depends

from app.schemas.admin import (
    ApproveExpandRequest,
    CreateAppRequest,
    CreateExperimentRequest,
    CreateVersionRequest,
    ExperimentMetricsQuery,
    ListAppsQuery,
    ListExperimentsQuery,
    ListRequestsQuery,
    ListVersionsQuery,
    RollbackRequest,
    SetStableVersionRequest,
    SetVersionStatusRequest,
    StopExperimentRequest,
    TimeseriesMetricsQuery,
    UpdateExperimentRequest,
    UpdateVersionRequest,
)
from app.schemas.common import OperatorPayload
from app.services.app_service import AppService
from app.services.approval_service import ApprovalService
from app.services.decision_service import DecisionService
from app.services.experiment_service import ExperimentService
from app.services.metrics_service import MetricsService
from app.services.rollback_service import RollbackService
from app.services.trace_service import TraceService
from app.services.version_service import VersionService

router = APIRouter(prefix="/canary/api/v1")

app_service = AppService()
version_service = VersionService()
experiment_service = ExperimentService()
trace_service = TraceService()
metrics_service = MetricsService()
decision_service = DecisionService()
rollback_service = RollbackService()
approval_service = ApprovalService()


@router.post("/apps", status_code=201)
def create_app(payload: CreateAppRequest) -> dict:
    return {"code": 0, "message": "success", "data": app_service.create_app(payload.model_dump())}


@router.get("/apps")
def list_apps(query: ListAppsQuery = Depends()) -> dict:
    return {"code": 0, "message": "success", "data": app_service.list_apps(query.model_dump())}


@router.get("/apps/{app_id}")
def get_app(app_id: str) -> dict:
    return {"code": 0, "message": "success", "data": app_service.get_app(app_id)}


@router.post("/apps/{app_id}/versions", status_code=201)
def create_version(app_id: str, payload: CreateVersionRequest) -> dict:
    return {"code": 0, "message": "success", "data": version_service.create_version(app_id, payload.model_dump())}


@router.get("/apps/{app_id}/versions")
def list_versions(app_id: str, query: ListVersionsQuery = Depends()) -> dict:
    return {"code": 0, "message": "success", "data": version_service.list_versions(app_id, query.model_dump())}


@router.get("/versions/{version_id}")
def get_version(version_id: str) -> dict:
    return {"code": 0, "message": "success", "data": version_service.get_version(version_id)}


@router.put("/versions/{version_id}")
def update_version(version_id: str, payload: UpdateVersionRequest) -> dict:
    return {"code": 0, "message": "success", "data": version_service.update_version(version_id, payload.model_dump())}


@router.get("/versions/{version_id}/diff/{target_version_id}")
def diff_versions(version_id: str, target_version_id: str) -> dict:
    return {"code": 0, "message": "success", "data": version_service.diff_versions(version_id, target_version_id)}


@router.post("/apps/{app_id}/stable-version")
def set_stable_version(app_id: str, payload: SetStableVersionRequest) -> dict:
    return {"code": 0, "message": "success", "data": version_service.set_stable_version(app_id, payload.version_id)}


@router.post("/versions/{version_id}/status")
def set_version_status(version_id: str, payload: SetVersionStatusRequest) -> dict:
    return {
        "code": 0,
        "message": "success",
        "data": version_service.set_version_status(version_id, payload.status, payload.operator),
    }


@router.post("/experiments", status_code=201)
def create_experiment(payload: CreateExperimentRequest) -> dict:
    return {"code": 0, "message": "success", "data": experiment_service.create_experiment(payload.model_dump())}


@router.post("/experiments/{experiment_id}/start")
def start_experiment(experiment_id: str, payload: OperatorPayload) -> dict:
    return {"code": 0, "message": "success", "data": experiment_service.start_experiment(experiment_id, payload.operator)}


@router.post("/experiments/{experiment_id}/stop")
def stop_experiment(experiment_id: str, payload: StopExperimentRequest) -> dict:
    return {
        "code": 0,
        "message": "success",
        "data": experiment_service.stop_experiment(experiment_id, payload.operator, payload.reason),
    }


@router.get("/experiments")
def list_experiments(query: ListExperimentsQuery = Depends()) -> dict:
    return {"code": 0, "message": "success", "data": experiment_service.list_experiments(query.model_dump())}


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: str) -> dict:
    return {"code": 0, "message": "success", "data": experiment_service.get_experiment(experiment_id)}


@router.put("/experiments/{experiment_id}")
def update_experiment(experiment_id: str, payload: UpdateExperimentRequest) -> dict:
    return {"code": 0, "message": "success", "data": experiment_service.update_experiment(experiment_id, payload.model_dump())}


@router.get("/requests/{request_id}")
def get_request(request_id: str) -> dict:
    return {"code": 0, "message": "success", "data": trace_service.get_request(request_id)}


@router.get("/requests")
def list_requests(query: ListRequestsQuery = Depends()) -> dict:
    return {"code": 0, "message": "success", "data": trace_service.list_requests(query.model_dump())}


@router.get("/experiments/{experiment_id}/metrics")
def get_metrics(experiment_id: str, query: ExperimentMetricsQuery = Depends()) -> dict:
    return {
        "code": 0,
        "message": "success",
        "data": metrics_service.get_experiment_metrics(experiment_id, query.start_time, query.end_time),
    }


@router.get("/experiments/{experiment_id}/metrics/timeseries")
def get_metrics_timeseries(experiment_id: str, query: TimeseriesMetricsQuery = Depends()) -> dict:
    return {
        "code": 0,
        "message": "success",
        "data": metrics_service.get_timeseries(
            experiment_id, query.metric, query.interval, query.start_time, query.end_time
        ),
    }


@router.get("/experiments/{experiment_id}/decision")
def get_decision(experiment_id: str) -> dict:
    return {"code": 0, "message": "success", "data": decision_service.get_current(experiment_id)}


@router.post("/experiments/{experiment_id}/decision/recompute")
def recompute_decision(experiment_id: str, payload: OperatorPayload) -> dict:
    return {"code": 0, "message": "success", "data": decision_service.recompute(experiment_id)}


@router.post("/experiments/{experiment_id}/rollback")
def rollback(experiment_id: str, payload: RollbackRequest) -> dict:
    return {
        "code": 0,
        "message": "success",
        "data": rollback_service.rollback(experiment_id, payload.operator, payload.reason),
    }


@router.get("/experiments/{experiment_id}/rollback-logs")
def list_rollback_logs(experiment_id: str) -> dict:
    return {"code": 0, "message": "success", "data": rollback_service.list_logs(experiment_id)}


@router.get("/experiments/{experiment_id}/expand-recommendation")
def get_expand_recommendation(experiment_id: str) -> dict:
    return {"code": 0, "message": "success", "data": decision_service.get_expand_recommendation(experiment_id)}


@router.post("/experiments/{experiment_id}/approve-expand")
def approve_expand(experiment_id: str, payload: ApproveExpandRequest) -> dict:
    return {
        "code": 0,
        "message": "success",
        "data": approval_service.approve_expand(
            experiment_id,
            operator=payload.operator,
            approved=payload.approved,
            approved_split=payload.approved_split,
            approval_reason=payload.approval_reason,
        ),
    }


@router.get("/experiments/{experiment_id}/approval-logs")
def list_approval_logs(experiment_id: str) -> dict:
    return {"code": 0, "message": "success", "data": approval_service.list_logs(experiment_id)}
