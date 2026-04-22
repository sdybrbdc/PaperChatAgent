from __future__ import annotations

from collections.abc import AsyncIterator

from paperchat.api.errcode import AppError
from paperchat.api.responses.sse import encode_sse, now_iso
from paperchat.database.dao import memory_store
from paperchat.services.stream import translate_chat_stream_part
from paperchat.workflows.chat_graph import build_chat_graph


class ChatService:
    def __init__(self) -> None:
        self.graph = build_chat_graph()

    def get_inbox_payload(self, user_id: str) -> dict:
        inbox, session = memory_store.get_or_create_default_session(user_id)
        return {
            "conversation": memory_store.as_inbox_payload(inbox),
            "current_session": memory_store.as_chat_session_payload(session),
        }

    def get_messages_payload(self, user_id: str, session_id: str, before: str | None, limit: int) -> dict:
        session = memory_store.get_chat_session(session_id)
        if session is None or session.user_id != user_id:
            raise AppError(status_code=404, code="CHAT_CONVERSATION_NOT_FOUND", message="会话不存在")

        messages = memory_store.list_messages(session_id)
        if before:
            cut_index = next((index for index, item in enumerate(messages) if item.id == before), len(messages))
            messages = messages[:cut_index]
        items = messages[-limit:]
        return {
            "items": [memory_store.as_message_payload(message) for message in items],
            "paging": {
                "before": before,
                "limit": limit,
                "has_more": len(messages) > len(items),
            },
        }

    async def stream_reply(
        self,
        *,
        user_id: str,
        session_id: str,
        content: str,
        client_message_id: str | None,
    ) -> AsyncIterator[str]:
        session = memory_store.get_chat_session(session_id)
        if session is None or session.user_id != user_id:
            raise AppError(status_code=404, code="CHAT_CONVERSATION_NOT_FOUND", message="会话不存在")

        memory_store.add_message(
            session_id=session_id,
            user_id=user_id,
            role="user",
            message_type="chat",
            content=content,
        )

        accumulated = ""
        yield encode_sse(
            "message.started",
            {
                "conversation_id": session_id,
                "session_id": session_id,
                "client_message_id": client_message_id,
            },
        )
        yield encode_sse("ping", {"ts": now_iso()})

        try:
            async for part in self.graph.astream(
                {"session_scope": session.scope, "user_input": content},
                stream_mode=["messages", "updates", "custom"],
            ):
                for event_name, payload in translate_chat_stream_part(part):
                    if event_name == "message.delta":
                        accumulated += payload["delta"]
                        payload = {
                            "delta": payload["delta"],
                            "accumulated": accumulated,
                        }
                    yield encode_sse(event_name, payload)
        except Exception as exc:
            yield encode_sse(
                "message.failed",
                {
                    "code": "CHAT_STREAM_FAILED",
                    "message": str(exc),
                },
            )
            return

        final_text = accumulated.strip()
        if not final_text:
            yield encode_sse(
                "message.failed",
                {
                    "code": "CHAT_STREAM_FAILED",
                    "message": "模型未返回有效内容",
                },
            )
            return

        message_type = "task_suggestion" if any(keyword in content for keyword in ["研究", "任务", "工作区"]) else "chat"
        metadata: dict = {}
        if message_type == "task_suggestion":
            metadata["taskSuggestion"] = {
                "title": "AI 建议的研究任务",
                "topic": content,
                "sources": "默认聊天上下文 + 用户后续上传资料",
                "outputs": "研究工作区、主题探索包、带引用依据的问答上下文",
                "nextStep": "继续补充关键词、范围或上传论文，然后创建任务",
                "statusLabel": "可创建工作区",
            }

        assistant_message = memory_store.add_message(
            session_id=session_id,
            user_id=None,
            role="assistant",
            message_type=message_type,
            content=final_text,
            metadata=metadata,
        )
        yield encode_sse("message.completed", {"message": memory_store.as_message_payload(assistant_message)})


chat_service = ChatService()
