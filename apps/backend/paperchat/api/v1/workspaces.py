from __future__ import annotations

from secrets import token_urlsafe

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from paperchat.api.errcode import AppError
from paperchat.api.responses import APIResponse, ok
from paperchat.auth import get_current_user
from paperchat.database.dao import memory_store


router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""


@router.post("", response_model=APIResponse)
async def create_workspace(payload: CreateWorkspaceRequest, request: Request, user=Depends(get_current_user)):
    workspace = memory_store.find_workspace_by_name(user_id=user.id, name=payload.name)
    if workspace is None:
        workspace = memory_store.create_workspace(user_id=user.id, name=payload.name, description=payload.description)
    return ok(request, data=memory_store.as_workspace_payload(workspace))


@router.get("", response_model=APIResponse)
async def list_workspaces(request: Request, user=Depends(get_current_user)):
    items = [memory_store.as_workspace_payload(item) for item in memory_store.list_workspaces(user.id)]
    return ok(
        request,
        data={
            "items": items,
            "page": 1,
            "page_size": len(items) or 20,
            "total": len(items),
            "has_more": False,
        },
    )


@router.get("/{workspace_id}", response_model=APIResponse)
async def get_workspace(workspace_id: str, request: Request, user=Depends(get_current_user)):
    workspace = memory_store.get_workspace(workspace_id)
    if workspace is None or workspace.user_id != user.id:
        raise AppError(status_code=404, code="WORKSPACE_NOT_FOUND", message="工作区不存在")
    return ok(request, data=memory_store.as_workspace_payload(workspace))


@router.post("/{workspace_id}/share-link", response_model=APIResponse)
async def create_share_link(workspace_id: str, request: Request, user=Depends(get_current_user)):
    workspace = memory_store.get_workspace(workspace_id)
    if workspace is None or workspace.user_id != user.id:
        raise AppError(status_code=404, code="WORKSPACE_NOT_FOUND", message="工作区不存在")
    share_token = workspace.share_token or token_urlsafe(16)
    workspace = memory_store.update_workspace(workspace_id, share_token=share_token)
    return ok(
        request,
        data={
            "workspace_id": workspace.id,
            "share_token": workspace.share_token,
            "share_url": f"/share/workspaces/{workspace.share_token}",
        },
    )
