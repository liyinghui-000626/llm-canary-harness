from __future__ import annotations

from typing import Any

from app.core.repository_provider import get_repository
from app.core.exceptions import AppError
from app.domain.enums.status import AppStatus
from app.utils.id_utils import id_generator
from app.utils.time_utils import utcnow_iso


class AppService:
    def create_app(self, payload: dict) -> dict:
        repository = get_repository()
        if repository.get_application_by_name(payload["app_name"]):
            raise AppError("app_name already exists", code=40901, status_code=409)

        app_id = id_generator.next_id("app")
        now = utcnow_iso()
        application = {
            "app_id": app_id,
            "app_name": payload["app_name"],
            "app_type": payload["app_type"],
            "description": payload.get("description"),
            "owner": payload["owner"],
            "business_scene": payload.get("business_scene"),
            "stable_version_id": None,
            "status": AppStatus.ACTIVE.value,
            "created_at": now,
            "updated_at": now,
        }
        return repository.create_application(application)

    def list_apps(self, filters: dict) -> dict:
        repository = get_repository()
        items = repository.list_applications(filters)
        enriched = []
        for item in items:
            running_experiments = repository.list_running_experiments(item["app_id"])
            running_experiment = running_experiments[0]["experiment_id"] if running_experiments else None
            enriched.append({**item, "running_experiment_id": running_experiment})

        return paginate(enriched, filters["page"], filters["page_size"])

    def get_app(self, app_id: str) -> dict:
        application = get_repository().get_application(app_id)
        if not application:
            raise AppError("app not found", code=40401, status_code=404)
        return application


def paginate(items: list[dict[str, Any]], page: int, page_size: int) -> dict[str, Any]:
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "total": len(items),
        "page": page,
        "page_size": page_size,
        "items": items[start:end],
    }
