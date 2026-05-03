from __future__ import annotations

import hashlib
from typing import Any

from app.core.exceptions import AppError
from app.core.repository_provider import get_repository
from app.services.app_service import AppService
from app.services.experiment_service import ExperimentService


class RoutingService:
    def __init__(self) -> None:
        self.app_service = AppService()
        self.experiment_service = ExperimentService()

    def resolve_route(self, app_id: str, user_id: str, metadata: dict[str, Any] | None) -> dict[str, Any]:
        app = self.app_service.get_app(app_id)
        running_experiment = self.experiment_service.get_running_experiment(app_id, required=False)

        if running_experiment:
            return self._route_with_experiment(running_experiment, user_id, metadata or {})

        stable_version_id = app.get("stable_version_id")
        if not stable_version_id:
            raise AppError("no stable version available", code=40005, status_code=400)
        version = get_repository().get_version(stable_version_id)
        assert version is not None
        return {
            "experiment_id": None,
            "version_id": stable_version_id,
            "version": version,
            "routing_reason": "stable_version_fallback",
        }

    def _route_with_experiment(
        self,
        experiment: dict[str, Any],
        user_id: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        routing_rules = experiment["routing_rules"]
        whitelist = set(routing_rules.get("whitelist_user_ids", []))
        if user_id in whitelist:
            version_id = experiment["treatment_version_id"]
            return self._route_result(experiment, version_id, "whitelist_hit_treatment")

        channels = routing_rules.get("channels", [])
        incoming_channel = metadata.get("channel")
        if channels and incoming_channel not in channels:
            version_id = experiment["control_version_id"]
            return self._route_result(experiment, version_id, "channel_not_match_control")

        bucket = self._stable_bucket(user_id)
        if bucket < experiment["traffic_treatment"]:
            version_id = experiment["treatment_version_id"]
            return self._route_result(experiment, version_id, "hash_bucket_hit_treatment")

        version_id = experiment["control_version_id"]
        return self._route_result(experiment, version_id, "hash_bucket_hit_control")

    def _route_result(self, experiment: dict[str, Any], version_id: str, reason: str) -> dict[str, Any]:
        version = get_repository().get_version(version_id)
        assert version is not None
        return {
            "experiment_id": experiment["experiment_id"],
            "version_id": version_id,
            "version": version,
            "routing_reason": reason,
        }

    def _stable_bucket(self, user_id: str) -> int:
        digest = hashlib.md5(user_id.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % 100
