from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from paperchat.api.responses import APIResponse, ok
from paperchat.auth import get_current_user
from paperchat.services.chat import chat_service


router = APIRouter(prefix="/conversations", tags=["Conversations"])


class SendMessageStreamRequest(BaseModel):
    content: str = Field(min_length=1)
    client_message_id: str | None = None
    attachment_ids: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


@router.get("/inbox", response_model=APIResponse)
async def get_inbox(request: Request, user=Depends(get_current_user)):
    return ok(request, data=chat_service.get_inbox_payload(user.id))


@router.get("/{conversation_id}/messages", response_model=APIResponse)
async def get_messages(
    conversation_id: str,
    request: Request,
    before: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    user=Depends(get_current_user),
):
    return ok(request, data=chat_service.get_messages_payload(user.id, conversation_id, before, limit))


@router.post("/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: str,
    payload: SendMessageStreamRequest,
    user=Depends(get_current_user),
):
    return StreamingResponse(
        chat_service.stream_reply(
            user_id=user.id,
            session_id=conversation_id,
            content=payload.content,
            client_message_id=payload.client_message_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
