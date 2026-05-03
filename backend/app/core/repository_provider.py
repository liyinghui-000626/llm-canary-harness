from __future__ import annotations

import os
from typing import cast

from app.repositories.base import CanaryRepository
from app.repositories.fake_repository import FakeCanaryRepository
from app.repositories.milvus.canary_repository import MilvusCanaryRepository

_repository_override: CanaryRepository | None = None
_default_repository: CanaryRepository | None = None


def get_repository() -> CanaryRepository:
    global _default_repository
    if _repository_override is not None:
        return _repository_override
    if _default_repository is None:
        backend = os.getenv("CANARY_REPOSITORY_BACKEND", "milvus").lower()
        if backend == "fake":
            _default_repository = FakeCanaryRepository()
        else:
            _default_repository = MilvusCanaryRepository()
    return _default_repository


def set_repository_override(repository: CanaryRepository | None) -> None:
    global _repository_override
    _repository_override = repository


def reset_default_repository() -> None:
    global _default_repository
    _default_repository = None
