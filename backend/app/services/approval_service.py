from __future__ import annotations

from app.core.exceptions import AppError
from app.core.repository_provider import get_repository
from app.domain.enums.status import ExperimentStatus
from app.services.decision_service import DecisionService
from app.services.experiment_service import ExperimentService
from app.utils.id_utils import id_generator
from app.utils.time_utils import utcnow_iso


class ApprovalService:
    def __init__(self) -> None:
        self.experiment_service = ExperimentService()
        self.decision_service = DecisionService()

    def approve_expand(
        self,
        experiment_id: str,
        operator: str,
        approved: bool,
        approved_split: dict[str, int] | None,
        approval_reason: str | None,
    ) -> dict:
        experiment = self.experiment_service.get_experiment(experiment_id)
        if experiment["status"] != ExperimentStatus.RUNNING.value:
            raise AppError("experiment is not running", code=40908, status_code=409)

        recommendation = self.decision_service.get_expand_recommendation(experiment_id)
        if recommendation["decision_type"] != "recommend_expand":
            raise AppError("no expand recommendation available", code=40909, status_code=409)

        approval_id = id_generator.next_id("ap")
        now = utcnow_iso()
        old_split = {"control": experiment["traffic_control"], "treatment": experiment["traffic_treatment"]}
        new_split = old_split.copy()
        status = "rejected"
        repository = get_repository()

        if approved:
            assert approved_split is not None
            new_split = approved_split
            repository.update_experiment(
                experiment_id,
                {
                    "traffic_control": approved_split["control"],
                    "traffic_treatment": approved_split["treatment"],
                    "updated_at": now,
                },
            )
            status = "approved"

        log_item = {
            "approval_id": approval_id,
            "experiment_id": experiment_id,
            "current_split": f"{old_split['control']}/{old_split['treatment']}",
            "recommended_split": recommendation["recommended_split"],
            "approved_by": operator,
            "approval_reason": approval_reason,
            "status": status,
            "created_at": now,
        }
        repository.append_approval_log(experiment_id, log_item)
        return {
            "approval_id": approval_id,
            "experiment_id": experiment_id,
            "old_split": old_split,
            "new_split": new_split,
            "approved_by": operator,
            "status": status,
            "approved_at": now,
        }

    def list_logs(self, experiment_id: str) -> dict:
        self.experiment_service.get_experiment(experiment_id)
        return {"items": get_repository().list_approval_logs(experiment_id)}
