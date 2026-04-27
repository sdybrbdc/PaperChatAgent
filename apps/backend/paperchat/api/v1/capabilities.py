from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from paperchat.api.responses import APIResponse, ok
from paperchat.auth import get_current_user
from paperchat.schemas.capabilities import CapabilityKind, ExecuteCapabilityRequest
from paperchat.services.capabilities import capability_service


router = APIRouter(prefix="/capabilities", tags=["Capabilities"])


@router.get("", response_model=APIResponse)
async def list_capabilities(
    request: Request,
    kind: CapabilityKind | None = Query(default=None),
    user=Depends(get_current_user),
):
    return ok(request, data=capability_service.list_capabilities_payload(user_id=user.id, kind=kind))


@router.get("/logs", response_model=APIResponse)
async def list_capability_logs(
    request: Request,
    capability_key: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=capability_service.list_logs_payload(user_id=user.id, capability_key=capability_key, limit=limit),
    )


@router.get("/{capability_key:path}", response_model=APIResponse)
async def get_capability(capability_key: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=capability_service.get_capability_payload(user_id=user.id, capability_key=capability_key))


@router.post("/{capability_key:path}/execute", response_model=APIResponse)
async def execute_capability(
    capability_key: str,
    payload: ExecuteCapabilityRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=await capability_service.execute_capability_payload(
            user_id=user.id,
            capability_key=capability_key,
            input_payload=payload.input,
            context=payload.context,
            dry_run=payload.dry_run,
        ),
    )
