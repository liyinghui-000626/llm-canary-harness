from __future__ import annotations

from typing import Any

from app.core.repository_provider import get_repository
from app.services.experiment_service import ExperimentService
from app.services.metrics_service import MetricsService
from app.utils.time_utils import utcnow_iso


class DecisionService:
    def __init__(self) -> None:
        self.experiment_service = ExperimentService()
        self.metrics_service = MetricsService()

    def recompute(self, experiment_id: str) -> dict[str, Any]:
        experiment = self.experiment_service.get_experiment(experiment_id)
        metrics = self.metrics_service.get_experiment_metrics(experiment_id)
        treatment = metrics["treatment"]
        control = metrics["control"]
        guardrails = experiment["guardrails"]

        triggered_rules: list[dict[str, str]] = []
        decision_type = "keep_observing"
        risk_level = "medium"
        recommended_next_split = None
        requires_manual_approval = False

        if treatment["request_count"] < guardrails["min_sample_size"]:
            triggered_rules.append(
                {
                    "rule_name": "sample_size_not_enough",
                    "reason": f"treatment.request_count={treatment['request_count']} < min_sample_size={guardrails['min_sample_size']}",
                }
            )
        else:
            if treatment["error_rate"] > guardrails["max_error_rate"]:
                triggered_rules.append(
                    {
                        "rule_name": "max_error_rate",
                        "reason": f"treatment.error_rate={treatment['error_rate']} > {guardrails['max_error_rate']}",
                    }
                )
            control_latency = max(control["avg_latency_ms"], 1)
            latency_ratio = treatment["avg_latency_ms"] / control_latency if treatment["request_count"] else 0
            if latency_ratio > guardrails["max_latency_ratio"]:
                triggered_rules.append(
                    {
                        "rule_name": "max_latency_ratio",
                        "reason": f"treatment.avg_latency_ms={treatment['avg_latency_ms']} > control.avg_latency_ms*{guardrails['max_latency_ratio']}",
                    }
                )

            if triggered_rules:
                decision_type = "rollback"
                risk_level = "high"
            else:
                decision_type = "recommend_expand"
                risk_level = "low"
                recommended_next_split = self._recommend_split(experiment["traffic_treatment"])
                requires_manual_approval = True

        decision = {
            "experiment_id": experiment_id,
            "decision_type": decision_type,
            "risk_level": risk_level,
            "triggered_rules": triggered_rules,
            "recommended_next_split": recommended_next_split,
            "requires_manual_approval": requires_manual_approval,
            "evaluated_at": utcnow_iso(),
        }
        return get_repository().set_decision(experiment_id, decision)

    def get_current(self, experiment_id: str) -> dict[str, Any]:
        return get_repository().get_decision(experiment_id) or self.recompute(experiment_id)

    def get_expand_recommendation(self, experiment_id: str) -> dict[str, Any]:
        experiment = self.experiment_service.get_experiment(experiment_id)
        decision = self.get_current(experiment_id)
        reasons = [item["rule_name"] for item in decision["triggered_rules"]]
        if decision["decision_type"] == "recommend_expand":
            reasons = ["sample_size_ready", "error_rate_stable", "latency_within_guardrail"]
        return {
            "experiment_id": experiment_id,
            "current_split": f"{experiment['traffic_control']}/{experiment['traffic_treatment']}",
            "recommended_split": decision["recommended_next_split"],
            "decision_type": decision["decision_type"],
            "risk_level": decision["risk_level"],
            "reasons": reasons,
            "requires_manual_approval": decision["requires_manual_approval"],
            "generated_at": decision["evaluated_at"],
        }

    def _recommend_split(self, current_treatment: int) -> str:
        next_treatment = min(100, current_treatment + 20)
        next_control = 100 - next_treatment
        return f"{next_control}/{next_treatment}"
