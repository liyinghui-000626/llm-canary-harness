from __future__ import annotations

from enum import Enum


class AppStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class VersionStatus(str, Enum):
    DRAFT = "draft"
    STABLE = "stable"


class ExperimentStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    ROLLED_BACK = "rolled_back"


class RequestStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"

