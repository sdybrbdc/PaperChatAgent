from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from paperchat.api.responses import APIResponse, ok
from paperchat.auth import get_current_user
from paperchat.schemas.models import (
    ModelProviderCreate,
    ModelProviderUpdate,
    ModelRouteCreate,
    ModelRouteTestRequest,
    ModelRouteUpdate,
    ModelUsageLogCreate,
)
from paperchat.services.model_router import model_router_service


router = APIRouter(prefix="/models", tags=["Models"])


class ModelSlotTestRequest(BaseModel):
    route_key: str = Field(min_length=1)
    prompt: str = Field(default="ping", max_length=2000)
    metadata: dict = Field(default_factory=dict)


@router.get("/providers", response_model=APIResponse)
async def list_providers(request: Request, user=Depends(get_current_user)):
    return ok(request, data=model_router_service.list_providers_payload(user_id=user.id))


@router.post("/providers", response_model=APIResponse)
async def create_provider(payload: ModelProviderCreate, request: Request, user=Depends(get_current_user)):
    return ok(request, data=model_router_service.create_provider_payload(user_id=user.id, payload=payload))


@router.get("/providers/{provider_id}", response_model=APIResponse)
async def get_provider(provider_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=model_router_service.get_provider_payload(user_id=user.id, provider_id=provider_id))


@router.put("/providers/{provider_id}", response_model=APIResponse)
async def update_provider(
    provider_id: str,
    payload: ModelProviderUpdate,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(request, data=model_router_service.update_provider_payload(user_id=user.id, provider_id=provider_id, payload=payload))


@router.delete("/providers/{provider_id}", response_model=APIResponse)
async def delete_provider(provider_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=model_router_service.delete_provider_payload(user_id=user.id, provider_id=provider_id))


@router.get("/routes", response_model=APIResponse)
async def list_routes(request: Request, user=Depends(get_current_user)):
    return ok(request, data=model_router_service.list_routes_payload(user_id=user.id))


@router.post("/routes", response_model=APIResponse)
async def create_route(payload: ModelRouteCreate, request: Request, user=Depends(get_current_user)):
    return ok(request, data=model_router_service.create_route_payload(user_id=user.id, payload=payload))


@router.get("/routes/{route_id}", response_model=APIResponse)
async def get_route(route_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=model_router_service.get_route_payload(user_id=user.id, route_id=route_id))


@router.put("/routes/{route_id}", response_model=APIResponse)
async def update_route(route_id: str, payload: ModelRouteUpdate, request: Request, user=Depends(get_current_user)):
    return ok(request, data=model_router_service.update_route_payload(user_id=user.id, route_id=route_id, payload=payload))


@router.delete("/routes/{route_id}", response_model=APIResponse)
async def delete_route(route_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=model_router_service.delete_route_payload(user_id=user.id, route_id=route_id))


@router.post("/routes/{route_id}/test", response_model=APIResponse)
async def test_route(
    route_id: str,
    payload: ModelRouteTestRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=model_router_service.test_route_payload(
            user_id=user.id,
            route_id=route_id,
            prompt=payload.prompt,
            metadata=payload.metadata,
        ),
    )


@router.post("/test", response_model=APIResponse)
async def test_route_by_key(
    payload: ModelSlotTestRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=model_router_service.test_route_payload(
            user_id=user.id,
            route_id=payload.route_key,
            prompt=payload.prompt,
            metadata=payload.metadata,
        ),
    )


@router.post("/usage-logs", response_model=APIResponse)
async def record_usage(payload: ModelUsageLogCreate, request: Request, user=Depends(get_current_user)):
    return ok(request, data=model_router_service.record_usage_payload(user_id=user.id, payload=payload))


@router.get("/usage-logs", response_model=APIResponse)
async def list_usage_logs(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=100, ge=1, le=500),
    user=Depends(get_current_user),
):
    start_at = datetime.now(timezone.utc) - timedelta(days=days)
    return ok(request, data=model_router_service.list_usage_payload(user_id=user.id, start_at=start_at, limit=limit))
