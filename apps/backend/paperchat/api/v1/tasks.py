from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from paperchat.api.errcode import AppError
from paperchat.api.responses import APIResponse, ok
from paperchat.api.responses.sse import encode_sse
from paperchat.auth import get_current_user
from paperchat.database.dao import memory_store
from paperchat.services.task import task_service


router = APIRouter(prefix="/tasks", tags=["Tasks"])


class CreateTaskRequest(BaseModel):
    source_session_id: str | None = None
    topic: str
    keywords: list[str] = Field(default_factory=list)
    source_config: dict = Field(default_factory=dict)


class ResumeTaskRequest(BaseModel):
    resume_from_node: str | None = None
    model_slot_overrides: dict[str, str] = Field(default_factory=dict)


@router.post("", response_model=APIResponse)
async def create_task(payload: CreateTaskRequest, request: Request, user=Depends(get_current_user)):
    task = await task_service.create_task(
        user_id=user.id,
        title=payload.topic,
        source_session_id=payload.source_session_id,
        keywords=payload.keywords,
        source_config=payload.source_config,
    )
    return ok(request, data=task)


@router.get("", response_model=APIResponse)
async def list_tasks(request: Request, user=Depends(get_current_user)):
    return ok(request, data=task_service.list_tasks(user.id))


@router.get("/{task_id}", response_model=APIResponse)
async def get_task(task_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=task_service.get_task(user.id, task_id))


@router.post("/{task_id}/retry", response_model=APIResponse)
async def retry_task(task_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=await task_service.retry_task(user_id=user.id, task_id=task_id))


@router.post("/{task_id}/resume", response_model=APIResponse)
async def resume_task(
    task_id: str,
    payload: ResumeTaskRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=await task_service.resume_task(
            user_id=user.id,
            task_id=task_id,
            resume_from_node=payload.resume_from_node,
            model_slot_overrides=payload.model_slot_overrides,
        ),
    )


@router.get("/{task_id}/report", response_model=APIResponse)
async def get_task_report(task_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=task_service.get_task_report(user_id=user.id, task_id=task_id))


@router.get("/{task_id}/events")
async def task_events(task_id: str, user=Depends(get_current_user)):
    task = memory_store.get_task(task_id)
    if task is None or task.user_id != user.id:
        raise AppError(status_code=404, code="TASK_NOT_FOUND", message="任务不存在")

    async def event_stream():
        snapshot = memory_store.task_snapshot(task_id)
        if snapshot:
            yield encode_sse("task.snapshot", snapshot)
            if snapshot["status"] in {"completed", "failed", "canceled", "paused"}:
                return

        queue = memory_store.subscribe_task_events(task_id)
        try:
            while True:
                event = await queue.get()
                yield encode_sse(event["event"], event["data"])
                if event["event"] in {"task.completed", "task.failed", "task.canceled", "task.paused"}:
                    break
        finally:
            memory_store.unsubscribe_task_events(task_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
