from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.repository_provider import reset_default_repository, set_repository_override
from app.repositories.fake_repository import FakeCanaryRepository
from app.utils.id_utils import id_generator


@pytest.fixture(autouse=True)
def fake_repository() -> Iterator[FakeCanaryRepository]:
    repository = FakeCanaryRepository()
    set_repository_override(repository)
    reset_default_repository()
    id_generator.reset()
    yield repository
    set_repository_override(None)
    reset_default_repository()
    id_generator.reset()
