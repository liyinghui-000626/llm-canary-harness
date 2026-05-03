from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AppError(Exception):
    """统一业务异常，便于在 FastAPI 层做一致化响应。"""

    message: str
    code: int = 40000
    status_code: int = 400

