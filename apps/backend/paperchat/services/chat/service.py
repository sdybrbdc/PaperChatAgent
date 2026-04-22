from __future__ import annotations

from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from paperchat.api.errcode import AppError
from paperchat.api.responses.sse import encode_sse, now_iso
from paperchat.database.dao import memory_store
from paperchat.providers import get_conversation_chat_model
from paperchat.services.stream import translate_chat_stream_part
from paperchat.workflows.chat_graph import build_chat_graph


class ChatService:
    def __init__(self) -> None:
        self.graph = build_chat_graph()
        self.summary_model = get_conversation_chat_model()

    def list_conversations_payload(self, user_id: str) -> dict:
        conversations = memory_store.list_conversations(user_id)
        if not conversations:
            _, session = memory_store.get_or_create_default_session(user_id)
            conversations = [session]
        return {
            "items": [memory_store.as_chat_session_payload(session) for session in conversations],
        }

    def create_conversation_payload(self, user_id: str) -> dict:
        session = memory_store.create_conversation(user_id=user_id, title="新聊天")
        return memory_store.as_chat_session_payload(session)

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

    def _build_recent_window(self, session_id: str, limit: int = 12, exclude_last: int = 0) -> list[BaseMessage]:
        messages = memory_store.get_recent_context_messages(session_id, limit + exclude_last)
        if exclude_last > 0:
            messages = messages[:-exclude_last]
        history: list[BaseMessage] = []
        for message in messages:
            if message.role == "user":
                history.append(HumanMessage(content=message.content))
            elif message.role == "assistant":
                history.append(AIMessage(content=message.content))
            elif message.role == "system":
                history.append(SystemMessage(content=message.content))
        return history

    async def _maybe_update_session_memory(self, session_id: str) -> None:
        session = memory_store.get_chat_session(session_id)
        if session is None:
            return

        unsummarized_messages = memory_store.get_messages_since(session_id, session.last_summarized_message_id)
        if len(unsummarized_messages) <= 16:
            return

        messages_to_summarize = unsummarized_messages[:-8]
        if not messages_to_summarize:
            return

        conversation_text = "\n".join(
            f"{message.role}: {message.content}" for message in messages_to_summarize
        )
        prompt = (
            "请把以下聊天历史压缩成后续对话可复用的长期摘要，"
            "保留：用户目标、已确认的约束、重要结论、待跟进问题。"
            "输出简洁中文摘要。\n\n"
            f"已有摘要：\n{session.memory_summary_text or '（暂无）'}\n\n"
            f"新增历史：\n{conversation_text}"
        )

        response = await self.summary_model.ainvoke([HumanMessage(content=prompt)])
        last_message_id = messages_to_summarize[-1].id
        memory_store.update_chat_session(
            session_id,
            memory_summary_text=response.content.strip(),
            last_summarized_message_id=last_message_id,
        )

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
                {
                    "session_scope": session.scope,
                    "session_id": session_id,
                    "user_input": content,
                    "recent_messages": self._build_recent_window(session_id, exclude_last=1),
                    "memory_summary_text": session.memory_summary_text,
                },
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

        assistant_message = memory_store.add_message(
            session_id=session_id,
            user_id=None,
            role="assistant",
            message_type="chat",
            content=final_text,
            metadata={},
        )
        await self._maybe_update_session_memory(session_id)
        yield encode_sse("message.completed", {"message": memory_store.as_message_payload(assistant_message)})


chat_service = ChatService()
