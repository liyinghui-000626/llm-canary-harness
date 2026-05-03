from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.admin.router import router as admin_router
from app.core.exceptions import AppError
from app.core.response import error_response

app = FastAPI(
    title="LLM Canary Harness Admin API",
    version="v1",
    docs_url="/canary/docs",
    openapi_url="/canary/openapi.json",
)
app.include_router(admin_router)


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_response(exc.code, exc.message))


@app.exception_handler(Exception)
async def handle_unknown_error(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content=error_response(50000, str(exc)))


@app.get("/canary")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "admin_api", "base_path": "/canary"}
