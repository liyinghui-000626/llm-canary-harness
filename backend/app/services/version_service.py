from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Any

from app.core.exceptions import AppError
from app.core.repository_provider import get_repository
from app.domain.enums.status import ExperimentStatus, VersionStatus
from app.services.app_service import AppService, paginate
from app.utils.id_utils import id_generator
from app.utils.time_utils import utcnow_iso


class VersionService:
    def __init__(self) -> None:
        self.app_service = AppService()

    def create_version(self, app_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        repository = get_repository()
        self.app_service.get_app(app_id)
        if self._find_version_by_name(app_id, payload["version_name"]):
            raise AppError("version_name already exists", code=40902, status_code=409)

        if payload.get("base_version_id"):
            self.get_version(payload["base_version_id"])

        version_id = id_generator.next_id("ver")
        now = utcnow_iso()
        version = {
            "version_id": version_id,
            "app_id": app_id,
            "version_name": payload["version_name"],
            "base_version_id": payload.get("base_version_id"),
            "prompt_template": payload["prompt_template"],
            "model_name": payload["model_name"],
            "endpoint_url": payload["endpoint_url"],
            "temperature": payload["temperature"],
            "top_p": payload["top_p"],
            "max_tokens": payload["max_tokens"],
            "rag_enabled": payload["rag_enabled"],
            "rag_config": payload.get("rag_config") or {},
            "output_schema": payload.get("output_schema") or {},
            "status": VersionStatus.DRAFT.value,
            "created_by": payload["created_by"],
            "created_at": now,
            "updated_at": now,
        }
        return repository.create_version(version)

    def list_versions(self, app_id: str, filters: dict[str, Any]) -> dict[str, Any]:
        self.app_service.get_app(app_id)
        items = get_repository().list_versions(app_id, filters)
        items.sort(key=lambda item: item["created_at"])
        return paginate(items, filters["page"], filters["page_size"])

    def get_version(self, version_id: str) -> dict[str, Any]:
        version = get_repository().get_version(version_id)
        if not version:
            raise AppError("version not found", code=40402, status_code=404)
        return version

    def update_version(self, version_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        version = self.get_version(version_id)
        repository = get_repository()
        app_id = version["app_id"]

        duplicate = self._find_version_by_name(app_id, payload["version_name"])
        if duplicate and duplicate["version_id"] != version_id:
            raise AppError("version_name already exists", code=40902, status_code=409)

        if payload.get("base_version_id"):
            base_version = self.get_version(payload["base_version_id"])
            if base_version["app_id"] != app_id:
                raise AppError("version does not belong to app", code=40002, status_code=400)

        updated = repository.update_version(
            version_id,
            {
                "version_name": payload["version_name"],
                "base_version_id": payload.get("base_version_id"),
                "prompt_template": payload["prompt_template"],
                "model_name": payload["model_name"],
                "endpoint_url": payload["endpoint_url"],
                "temperature": payload["temperature"],
                "top_p": payload["top_p"],
                "max_tokens": payload["max_tokens"],
                "rag_enabled": payload["rag_enabled"],
                "rag_config": payload.get("rag_config") or {},
                "output_schema": payload.get("output_schema") or {},
                "updated_at": utcnow_iso(),
            },
        )
        return updated

    def diff_versions(self, version_id: str, target_version_id: str) -> dict[str, Any]:
        source = self.get_version(version_id)
        target = self.get_version(target_version_id)
        diff_items: list[dict[str, Any]] = []
        self._walk_diff("", source, target, diff_items)
        ignored = {"version_id", "created_at", "updated_at"}
        diff_items = [item for item in diff_items if item["field"] not in ignored]
        return {
            "source_version_id": version_id,
            "target_version_id": target_version_id,
            "diff_items": diff_items,
        }

    def set_stable_version(self, app_id: str, version_id: str) -> dict[str, Any]:
        repository = get_repository()
        application = self.app_service.get_app(app_id)
        version = self.get_version(version_id)
        if version["app_id"] != app_id:
            raise AppError("version does not belong to app", code=40002, status_code=400)

        running = bool(repository.list_running_experiments(app_id))
        if running:
            raise AppError("running experiment exists", code=40903, status_code=409)

        for item in repository.list_versions(app_id, {}):
            if item["status"] == VersionStatus.STABLE.value:
                repository.update_version(item["version_id"], {"status": VersionStatus.DRAFT.value, "updated_at": utcnow_iso()})

        repository.update_version(version_id, {"status": VersionStatus.STABLE.value, "updated_at": utcnow_iso()})
        updated_application = repository.update_application(
            app_id,
            {"stable_version_id": version_id, "updated_at": utcnow_iso()},
        )
        return {
            "app_id": app_id,
            "stable_version_id": version_id,
            "updated_at": updated_application["updated_at"],
        }

    def set_version_status(self, version_id: str, status: str, operator: str) -> dict[str, Any]:
        version = self.get_version(version_id)
        app_id = version["app_id"]
        repository = get_repository()

        if status == VersionStatus.STABLE.value:
            self.set_stable_version(app_id, version_id)
            return self.get_version(version_id)

        if status != VersionStatus.DRAFT.value:
            raise AppError("invalid version status", code=40006, status_code=400)

        now = utcnow_iso()
        updated = repository.update_version(
            version_id,
            {
                "status": VersionStatus.DRAFT.value,
                "updated_at": now,
            },
        )
        application = self.app_service.get_app(app_id)
        if application.get("stable_version_id") == version_id:
            repository.update_application(
                app_id,
                {
                    "stable_version_id": None,
                    "updated_at": now,
                },
            )
        return updated

    def _find_version_by_name(self, app_id: str, version_name: str) -> dict[str, Any] | None:
        return next((item for item in get_repository().list_versions(app_id, {}) if item["version_name"] == version_name), None)

    def _walk_diff(
        self,
        prefix: str,
        source: dict[str, Any],
        target: dict[str, Any],
        diff_items: list[dict[str, Any]],
    ) -> None:
        keys = set(source) | set(target)
        for key in sorted(keys):
            field_name = f"{prefix}.{key}" if prefix else key
            source_value = source.get(key)
            target_value = target.get(key)
            if isinstance(source_value, dict) and isinstance(target_value, dict):
                self._walk_diff(field_name, source_value, target_value, diff_items)
            elif source_value != target_value:
                diff_items.append(
                    {
                        "field": field_name,
                        "source_value": deepcopy(source_value),
                        "target_value": deepcopy(target_value),
                    }
                )
