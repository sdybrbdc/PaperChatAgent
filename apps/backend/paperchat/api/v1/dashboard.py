from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from paperchat.api.responses import APIResponse, ok
from paperchat.auth import get_current_user
from paperchat.services.dashboard import dashboard_service


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=APIResponse)
async def overview(request: Request, days: int = Query(default=30, ge=1, le=365), user=Depends(get_current_user)):
    return ok(request, data=dashboard_service.overview_payload(user_id=user.id, days=days))


@router.get("/model-usage", response_model=APIResponse)
async def model_usage(request: Request, days: int = Query(default=30, ge=1, le=365), user=Depends(get_current_user)):
    return ok(request, data=dashboard_service.model_usage_payload(user_id=user.id, days=days))


@router.get("/task-distribution", response_model=APIResponse)
async def task_distribution(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
    user=Depends(get_current_user),
):
    return ok(request, data=dashboard_service.task_distribution_payload(user_id=user.id, days=days))


@router.get("/task-usage", response_model=APIResponse)
async def task_usage(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
    user=Depends(get_current_user),
):
    return ok(request, data=dashboard_service.task_distribution_payload(user_id=user.id, days=days))


@router.get("/tool-usage", response_model=APIResponse)
async def tool_usage(request: Request, days: int = Query(default=30, ge=1, le=365), user=Depends(get_current_user)):
    return ok(request, data=dashboard_service.tool_usage_payload(user_id=user.id, days=days))


@router.get("/activity", response_model=APIResponse)
async def activity(request: Request, days: int = Query(default=30, ge=1, le=365), user=Depends(get_current_user)):
    return ok(request, data=dashboard_service.activity_payload(user_id=user.id, days=days))


@router.get("/snapshot", response_model=APIResponse)
async def dashboard_snapshot(
    request: Request,
    days: int = Query(default=7, ge=1, le=365),
    user=Depends(get_current_user),
):
    return ok(request, data=dashboard_service.snapshot_payload(user_id=user.id, days=days))


@router.post("/snapshot", response_model=APIResponse)
async def create_dashboard_snapshot(
    request: Request,
    days: int = Query(default=7, ge=1, le=365),
    user=Depends(get_current_user),
):
    return ok(request, data=dashboard_service.snapshot_payload(user_id=user.id, days=days))
