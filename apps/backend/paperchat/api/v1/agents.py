from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from paperchat.api.errcode import AppError
from paperchat.api.responses import APIResponse, ok
from paperchat.auth import get_current_user
from paperchat.database.dao import memory_store
from paperchat.workflows import DEFAULT_WORKFLOW_ID, build_node_payloads, build_workflow_payload, list_workflow_payloads


router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/workflows", response_model=APIResponse)
async def list_workflows(request: Request, user=Depends(get_current_user)):
    return ok(request, data={"items": list_workflow_payloads()})


@router.get("/workflows/{workflow_id}", response_model=APIResponse)
async def get_workflow(workflow_id: str, request: Request, user=Depends(get_current_user)):
    payload = build_workflow_payload(workflow_id)
    if payload is None:
        raise AppError(status_code=404, code="WORKFLOW_NOT_FOUND", message="工作流不存在")
    return ok(request, data=payload)


@router.get("/workflows/{workflow_id}/nodes", response_model=APIResponse)
async def get_workflow_nodes(
    workflow_id: str,
    request: Request,
    task_id: str | None = Query(default=None),
    user=Depends(get_current_user),
):
    if workflow_id != DEFAULT_WORKFLOW_ID:
        raise AppError(status_code=404, code="WORKFLOW_NOT_FOUND", message="工作流不存在")

    node_runs = None
    if task_id:
        task = memory_store.get_task(task_id)
        if task is None or task.user_id != user.id:
            raise AppError(status_code=404, code="TASK_NOT_FOUND", message="任务不存在")
        node_runs = memory_store.list_task_node_runs(task_id)

    return ok(request, data={"items": build_node_payloads(node_runs)})
