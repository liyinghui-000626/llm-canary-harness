from __future__ import annotations

from app.core.repository_provider import get_repository
from app.domain.enums.status import ExperimentStatus
from app.services.decision_service import DecisionService
from app.services.rollback_service import RollbackService


class CanaryWorker:
    """V1 Worker 主任务。

    当前实现是同步扫描内存数据，后续替换成定时调度器即可。
    """

    def __init__(self) -> None:
        self.decision_service = DecisionService()
        self.rollback_service = RollbackService()

    def run_once(self) -> list[dict]:
        results: list[dict] = []
        for experiment in get_repository().list_experiments({}):
            if experiment["status"] != ExperimentStatus.RUNNING.value:
                continue
            decision = self.decision_service.recompute(experiment["experiment_id"])
            results.append(decision)
            if decision["decision_type"] == "rollback" and experiment["auto_rollback"]:
                reason = "; ".join(rule["reason"] for rule in decision["triggered_rules"])
                self.rollback_service.rollback(
                    experiment["experiment_id"],
                    operator="system",
                    reason=reason,
                    trigger_rule=",".join(rule["rule_name"] for rule in decision["triggered_rules"]),
                )
        return results
