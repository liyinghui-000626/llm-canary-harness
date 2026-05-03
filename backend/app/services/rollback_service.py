from __future__ import annotations

from typing import Any

from app.core.exceptions import AppError
from app.core.repository_provider import get_repository
from app.domain.enums.status import ExperimentStatus
from app.services.experiment_service import ExperimentService
from app.utils.id_utils import id_generator
from app.utils.time_utils import utcnow_iso


class RollbackService:
    def __init__(self) -> None:
        self.experiment_service = ExperimentService()

    def rollback(self, experiment_id: str, operator: str, reason: str, trigger_rule: str | None = None) -> dict[str, Any]:
        experiment = self.experiment_service.get_experiment(experiment_id)
        if experiment["status"] != ExperimentStatus.RUNNING.value:
            raise AppError("experiment is not running", code=40907, status_code=409)

        rollback_id = id_generator.next_id("rb")
        now = utcnow_iso()
        repository = get_repository()
        repository.update_experiment(
            experiment_id,
            {"status": ExperimentStatus.ROLLED_BACK.value, "stopped_at": now, "updated_at": now},
        )
        item = {
            "rollback_id": rollback_id,
            "experiment_id": experiment_id,
            "from_version_id": experiment["treatment_version_id"],
            "to_version_id": experiment["control_version_id"],
            "trigger_rule": trigger_rule,
            "reason": reason,
            "operator": operator,
            "status": "success",
            "created_at": now,
        }
        repository.append_rollback_log(experiment_id, item)
        return {
            "rollback_id": rollback_id,
            "experiment_id": experiment_id,
            "from_version_id": experiment["treatment_version_id"],
            "to_version_id": experiment["control_version_id"],
            "status": "success",
            "reason": reason,
            "rollback_at": now,
        }

    def list_logs(self, experiment_id: str) -> dict[str, Any]:
        self.experiment_service.get_experiment(experiment_id)
        return {"items": get_repository().list_rollback_logs(experiment_id)}
