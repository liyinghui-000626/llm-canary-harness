from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any

from app.repositories.base import CanaryRepository


@dataclass
class FakeCanaryRepository(CanaryRepository):
    applications: dict[str, dict[str, Any]] = field(default_factory=dict)
    versions: dict[str, dict[str, Any]] = field(default_factory=dict)
    experiments: dict[str, dict[str, Any]] = field(default_factory=dict)
    request_traces: dict[str, dict[str, Any]] = field(default_factory=dict)
    decisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    rollback_logs: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    approval_logs: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock)

    def create_application(self, application: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.applications[application["app_id"]] = deepcopy(application)
        return deepcopy(application)

    def get_application(self, app_id: str) -> dict[str, Any] | None:
        value = self.applications.get(app_id)
        return deepcopy(value) if value else None

    def get_application_by_name(self, app_name: str) -> dict[str, Any] | None:
        for item in self.applications.values():
            if item["app_name"] == app_name:
                return deepcopy(item)
        return None

    def list_applications(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        items = list(self.applications.values())
        return self._filter(items, filters)

    def update_application(self, app_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            current = self.applications[app_id]
            current.update(deepcopy(updates))
            return deepcopy(current)

    def create_version(self, version: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.versions[version["version_id"]] = deepcopy(version)
        return deepcopy(version)

    def get_version(self, version_id: str) -> dict[str, Any] | None:
        value = self.versions.get(version_id)
        return deepcopy(value) if value else None

    def list_versions(self, app_id: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        items = [item for item in self.versions.values() if item["app_id"] == app_id]
        return self._filter(items, filters)

    def update_version(self, version_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            current = self.versions[version_id]
            current.update(deepcopy(updates))
            return deepcopy(current)

    def create_experiment(self, experiment: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.experiments[experiment["experiment_id"]] = deepcopy(experiment)
        return deepcopy(experiment)

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        value = self.experiments.get(experiment_id)
        return deepcopy(value) if value else None

    def list_experiments(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        items = list(self.experiments.values())
        return self._filter(items, filters)

    def update_experiment(self, experiment_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            current = self.experiments[experiment_id]
            current.update(deepcopy(updates))
            return deepcopy(current)

    def list_running_experiments(self, app_id: str) -> list[dict[str, Any]]:
        return [
            deepcopy(item)
            for item in self.experiments.values()
            if item["app_id"] == app_id and item["status"] == "running"
        ]

    def create_request_trace(self, trace: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.request_traces[trace["request_id"]] = deepcopy(trace)
        return deepcopy(trace)

    def get_request_trace(self, request_id: str) -> dict[str, Any] | None:
        value = self.request_traces.get(request_id)
        return deepcopy(value) if value else None

    def list_request_traces(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        items = list(self.request_traces.values())
        start_time = filters.get("start_time")
        end_time = filters.get("end_time")
        filtered = self._filter(items, filters)
        if start_time:
            filtered = [item for item in filtered if self._parse(item["created_at"]) >= start_time]
        if end_time:
            filtered = [item for item in filtered if self._parse(item["created_at"]) <= end_time]
        return filtered

    def set_decision(self, experiment_id: str, decision: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.decisions[experiment_id] = deepcopy(decision)
        return deepcopy(decision)

    def get_decision(self, experiment_id: str) -> dict[str, Any] | None:
        value = self.decisions.get(experiment_id)
        return deepcopy(value) if value else None

    def append_rollback_log(self, experiment_id: str, rollback_log: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.rollback_logs.setdefault(experiment_id, []).append(deepcopy(rollback_log))
        return deepcopy(rollback_log)

    def list_rollback_logs(self, experiment_id: str) -> list[dict[str, Any]]:
        return deepcopy(self.rollback_logs.get(experiment_id, []))

    def append_approval_log(self, experiment_id: str, approval_log: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.approval_logs.setdefault(experiment_id, []).append(deepcopy(approval_log))
        return deepcopy(approval_log)

    def list_approval_logs(self, experiment_id: str) -> list[dict[str, Any]]:
        return deepcopy(self.approval_logs.get(experiment_id, []))

    def reset(self) -> None:
        with self.lock:
            self.applications.clear()
            self.versions.clear()
            self.experiments.clear()
            self.request_traces.clear()
            self.decisions.clear()
            self.rollback_logs.clear()
            self.approval_logs.clear()

    def _filter(self, items: list[dict[str, Any]], filters: dict[str, Any]) -> list[dict[str, Any]]:
        filtered = items
        for key, value in filters.items():
            if key in {"page", "page_size", "start_time", "end_time"}:
                continue
            if value is not None:
                filtered = [item for item in filtered if item.get(key) == value]
        return [deepcopy(item) for item in filtered]

    def _parse(self, value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

