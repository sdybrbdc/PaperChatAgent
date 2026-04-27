from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from paperchat.api.responses import APIResponse, ok
from paperchat.auth import get_current_user
from paperchat.schemas.tasks import CreateTaskRequest, TaskStatus
from paperchat.services.tasks import task_service


router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=APIResponse)
async def list_tasks(
    request: Request,
    status: TaskStatus | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=task_service.list_tasks_payload(user_id=user.id, status=status, limit=limit, offset=offset),
    )


@router.post("", response_model=APIResponse)
async def create_task(payload: CreateTaskRequest, request: Request, user=Depends(get_current_user)):
    return ok(
        request,
        data=await task_service.create_task_payload(
            user_id=user.id,
            workflow_id=payload.workflow_id,
            topic=payload.topic,
            conversation_id=payload.conversation_id,
            max_papers=payload.max_papers,
            start_background=payload.start_background,
        ),
    )


@router.get("/{task_id}", response_model=APIResponse)
async def get_task(task_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=task_service.get_task_payload(user_id=user.id, task_id=task_id))


@router.get("/{task_id}/events")
async def stream_task_events(task_id: str, request: Request, user=Depends(get_current_user)):
    return StreamingResponse(
        task_service.task_event_stream(user_id=user.id, task_id=task_id, request=request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{task_id}/cancel", response_model=APIResponse)
async def cancel_task(task_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=task_service.cancel_task_payload(user_id=user.id, task_id=task_id))
