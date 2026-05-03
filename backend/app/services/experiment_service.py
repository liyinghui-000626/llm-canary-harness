from __future__ import annotations

from typing import Any

from app.core.exceptions import AppError
from app.core.repository_provider import get_repository
from app.domain.enums.status import ExperimentStatus
from app.services.app_service import AppService, paginate
from app.services.version_service import VersionService
from app.utils.id_utils import id_generator
from app.utils.time_utils import utcnow_iso


class ExperimentService:
    def __init__(self) -> None:
        self.app_service = AppService()
        self.version_service = VersionService()

    def create_experiment(self, payload: dict[str, Any]) -> dict[str, Any]:
        repository = get_repository()
        self.app_service.get_app(payload["app_id"])
        control_version = self.version_service.get_version(payload["control_version_id"])
        treatment_version = self.version_service.get_version(payload["treatment_version_id"])
        if control_version["app_id"] != payload["app_id"] or treatment_version["app_id"] != payload["app_id"]:
            raise AppError("version does not belong to app", code=40003, status_code=400)

        running_experiment = self.get_running_experiment(payload["app_id"], required=False)
        if running_experiment:
            raise AppError("running experiment already exists", code=40904, status_code=409)

        experiment_id = id_generator.next_id("exp")
        now = utcnow_iso()
        experiment = {
            "experiment_id": experiment_id,
            "app_id": payload["app_id"],
            "experiment_name": payload["experiment_name"],
            "control_version_id": payload["control_version_id"],
            "treatment_version_id": payload["treatment_version_id"],
            "traffic_control": payload["traffic_control"],
            "traffic_treatment": payload["traffic_treatment"],
            "routing_rules": payload["routing_rules"],
            "guardrails": payload["guardrails"],
            "status": ExperimentStatus.CREATED.value,
            "auto_rollback": payload["auto_rollback"],
            "start_time": payload.get("start_time").isoformat().replace("+00:00", "Z")
            if payload.get("start_time")
            else None,
            "end_time": payload.get("end_time").isoformat().replace("+00:00", "Z")
            if payload.get("end_time")
            else None,
            "created_by": payload["created_by"],
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "stopped_at": None,
            "stop_reason": None,
        }
        return repository.create_experiment(experiment)

    def start_experiment(self, experiment_id: str, operator: str) -> dict[str, Any]:
        experiment = self.get_experiment(experiment_id)
        if experiment["status"] not in {ExperimentStatus.CREATED.value, ExperimentStatus.STOPPED.value}:
            raise AppError("experiment status conflict", code=40905, status_code=409)

        running_experiment = self.get_running_experiment(experiment["app_id"], required=False)
        if running_experiment and running_experiment["experiment_id"] != experiment_id:
            raise AppError("running experiment already exists", code=40904, status_code=409)

        app = self.app_service.get_app(experiment["app_id"])
        if app["stable_version_id"] != experiment["control_version_id"]:
            raise AppError("control version is not stable version", code=40004, status_code=400)

        started_at = utcnow_iso()
        updated = get_repository().update_experiment(
            experiment_id,
            {
                "status": ExperimentStatus.RUNNING.value,
                "started_at": started_at,
                "stopped_at": None,
                "stop_reason": None,
                "updated_at": started_at,
            },
        )
        return {
            "experiment_id": experiment_id,
            "status": updated["status"],
            "started_at": updated["started_at"],
        }

    def update_experiment(self, experiment_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        experiment = self.get_experiment(experiment_id)
        control_version = self.version_service.get_version(payload["control_version_id"])
        treatment_version = self.version_service.get_version(payload["treatment_version_id"])
        if control_version["app_id"] != experiment["app_id"] or treatment_version["app_id"] != experiment["app_id"]:
            raise AppError("version does not belong to app", code=40003, status_code=400)

        app = self.app_service.get_app(experiment["app_id"])
        if app["stable_version_id"] != payload["control_version_id"]:
            raise AppError("control version is not stable version", code=40004, status_code=400)

        now = utcnow_iso()
        updated = get_repository().update_experiment(
            experiment_id,
            {
                "experiment_name": payload["experiment_name"],
                "control_version_id": payload["control_version_id"],
                "treatment_version_id": payload["treatment_version_id"],
                "traffic_control": payload["traffic_control"],
                "traffic_treatment": payload["traffic_treatment"],
                "routing_rules": payload["routing_rules"],
                "guardrails": payload["guardrails"],
                "auto_rollback": payload["auto_rollback"],
                "updated_at": now,
            },
        )
        return updated

    def stop_experiment(self, experiment_id: str, operator: str, reason: str | None = None) -> dict[str, Any]:
        experiment = self.get_experiment(experiment_id)
        if experiment["status"] not in {ExperimentStatus.RUNNING.value, ExperimentStatus.CREATED.value}:
            raise AppError("experiment status conflict", code=40906, status_code=409)

        stopped_at = utcnow_iso()
        updated = get_repository().update_experiment(
            experiment_id,
            {
                "status": ExperimentStatus.STOPPED.value,
                "stopped_at": stopped_at,
                "updated_at": stopped_at,
                "stop_reason": reason,
            },
        )
        return {
            "experiment_id": experiment_id,
            "status": updated["status"],
            "stopped_at": updated["stopped_at"],
        }

    def list_experiments(self, filters: dict[str, Any]) -> dict[str, Any]:
        items = get_repository().list_experiments(filters)
        items.sort(key=lambda item: item["created_at"], reverse=True)
        return paginate(items, filters["page"], filters["page_size"])

    def get_experiment(self, experiment_id: str) -> dict[str, Any]:
        experiment = get_repository().get_experiment(experiment_id)
        if not experiment:
            raise AppError("experiment not found", code=40403, status_code=404)
        return experiment

    def get_running_experiment(self, app_id: str, required: bool = True) -> dict[str, Any] | None:
        running = get_repository().list_running_experiments(app_id)
        experiment = running[0] if running else None
        if required and not experiment:
            raise AppError("running experiment not found", code=40404, status_code=404)
        return experiment
