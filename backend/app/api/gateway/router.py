from __future__ import annotations

from fastapi import APIRouter

from app.schemas.gateway import GatewayInvokeRequest
from app.services.invoke_service import InvokeService

router = APIRouter(prefix="/canary/api/v1")
invoke_service = InvokeService()


@router.post("/gateway/invoke")
def gateway_invoke(payload: GatewayInvokeRequest) -> dict:
    return {"code": 0, "message": "success", "data": invoke_service.invoke(payload.model_dump())}
