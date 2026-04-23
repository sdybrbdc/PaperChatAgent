from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from paperchat.api.errcode import AppError
from paperchat.api.responses.sse import encode_sse, now_iso
from paperchat.database.dao import memory_store
from paperchat.services.stream import translate_chat_stream_part
from paperchat.workflows.chat_graph import build_chat_graph
from paperchat.workflows.guidance_graph import generate_guidance_analysis, generate_research_draft


class ChatService:
    def __init__(self) -> None:
        self.graph = build_chat_graph()

    def _require_conversation(self, user_id: str, conversation_id: str):
        conversation = memory_store.get_conversation(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            raise AppError(status_code=404, code="CHAT_CONVERSATION_NOT_FOUND", message="会话不存在")
        return conversation

    def list_conversations_payload(self, user_id: str) -> dict:
        conversations = memory_store.list_conversations(user_id)
        return {
            "items": [memory_store.as_conversation_payload(conversation) for conversation in conversations],
        }

    def create_conversation_payload(self, user_id: str) -> dict:
        conversation = memory_store.create_conversation(user_id=user_id, title="新聊天")
        return memory_store.as_conversation_payload(conversation)

    def get_conversation_payload(self, user_id: str, conversation_id: str) -> dict:
        conversation = self._require_conversation(user_id, conversation_id)
        return memory_store.as_conversation_payload(conversation)

    def get_messages_payload(self, user_id: str, conversation_id: str, before: str | None, limit: int) -> dict:
        self._require_conversation(user_id, conversation_id)
        messages = memory_store.list_messages(conversation_id)
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

    def get_guidance_payload(self, user_id: str, conversation_id: str) -> dict:
        self._require_conversation(user_id, conversation_id)
        snapshot = memory_store.get_guidance_snapshot(conversation_id)
        if snapshot is None:
            raise AppError(status_code=404, code="CHAT_GUIDANCE_NOT_FOUND", message="专业提示不存在")
        return memory_store.as_guidance_payload(snapshot)

    def _build_recent_window(self, conversation_id: str, *, limit: int = 12, exclude_last: int = 0) -> list[BaseMessage]:
        messages = memory_store.get_recent_context_messages(conversation_id, limit + exclude_last)
        if exclude_last > 0:
            messages = messages[:-exclude_last]
        history: list[BaseMessage] = []
        for message in messages:
            if message.role == "user":
                history.append(HumanMessage(content=message.content))
            elif message.role == "assistant":
                history.append(AIMessage(content=message.content))
            else:
                history.append(SystemMessage(content=message.content))
        return history

    def _build_transcript(self, conversation_id: str, *, limit: int = 16) -> str:
        messages = memory_store.get_recent_context_messages(conversation_id, limit)
        if not messages:
            return "暂无历史消息"
        return "\n".join(f"{message.role}: {message.content}" for message in messages)

    def _build_guidance_sections(self, analysis: dict[str, Any], *, draft: dict[str, Any] | None) -> list[dict[str, Any]]:
        status = analysis["status"]
        recognized = analysis["recognized"]
        suggested_steps = analysis["suggested_steps"]
        missing_info = analysis["missing_info"]

        sections: list[dict[str, Any]] = []

        sections.append(
            {
                "key": "status",
                "title": "当前判断",
                "style": "compact",
                "text": analysis["headline"],
                "items": [],
            }
        )

        identified_items = [
            f"主题：{recognized['topic']}" if recognized["topic"] else "",
            f"对象：{recognized['audience']}" if recognized["audience"] else "",
            f"目标：{recognized['goal']}" if recognized["goal"] else "",
            *recognized["outputs"],
        ]
        identified_items = [item for item in identified_items if item]

        if status in {"topic_exploration", "ready_for_draft"} and identified_items:
            sections.append(
                {
                    "key": "identified",
                    "title": "已识别信息",
                    "style": "info",
                    "text": "",
                    "items": identified_items[:4],
                }
            )

        if status == "needs_more_info" and missing_info:
            sections.append(
                {
                    "key": "missing",
                    "title": "待补充信息",
                    "style": "warning",
                    "text": "",
                    "items": missing_info,
                }
            )

        if status in {"topic_exploration", "needs_more_info", "ready_for_draft"} and suggested_steps:
            sections.append(
                {
                    "key": "steps",
                    "title": "建议下一步",
                    "style": "list",
                    "text": "",
                    "items": suggested_steps,
                }
            )

        if status == "ready_for_draft":
            sections.append(
                {
                    "key": "draft_entry",
                    "title": "研究草案",
                    "style": "draft_entry",
                    "text": "当前信息已基本收敛，可以手动生成研究草案。",
                    "items": [],
                }
            )

        if status == "draft_ready" and draft:
            sections.append(
                {
                    "key": "draft",
                    "title": "研究草案",
                    "style": "info",
                    "text": draft.get("title") or draft.get("topic") or "已生成研究草案",
                    "items": draft.get("next_actions", [])[:4],
                }
            )

        return sections

    async def _refresh_guidance(self, *, conversation_id: str, source_message_id: str | None = None) -> dict:
        conversation = memory_store.get_conversation(conversation_id)
        if conversation is None:
            raise AppError(status_code=404, code="CHAT_CONVERSATION_NOT_FOUND", message="会话不存在")

        snapshot = memory_store.get_guidance_snapshot(conversation_id)
        existing = memory_store.as_guidance_payload(snapshot) if snapshot else {}
        analysis = await generate_guidance_analysis(
            conversation_title=conversation.title,
            transcript=self._build_transcript(conversation_id),
            existing_headline=str(existing.get("headline") or ""),
            existing_draft=existing.get("draft") if isinstance(existing.get("draft"), dict) else None,
            should_suggest_title=(not conversation.title_finalized and conversation.completed_turn_count >= 3),
        )

        if not conversation.title_finalized and conversation.completed_turn_count >= 3:
            suggested_title = str(analysis.get("suggested_title") or "").strip()
            if suggested_title:
                conversation = memory_store.finalize_conversation_title(conversation_id, suggested_title) or conversation

        sections = self._build_guidance_sections(analysis, draft=existing.get("draft") if isinstance(existing.get("draft"), dict) else None)
        updated = memory_store.upsert_guidance_snapshot(
            conversation_id,
            status=analysis["status"],
            headline=analysis["headline"],
            sections=sections,
            draft=existing.get("draft") if isinstance(existing.get("draft"), dict) else None,
            source_message_id=source_message_id,
        )
        payload = memory_store.as_guidance_payload(updated)
        memory_store.append_realtime_event(
            conversation_id=conversation_id,
            event_type="guidance_updated",
            payload=payload,
        )
        return payload

    async def generate_draft_payload(self, *, user_id: str, conversation_id: str) -> dict:
        conversation = self._require_conversation(user_id, conversation_id)
        snapshot = memory_store.get_guidance_snapshot(conversation_id)
        guidance = memory_store.as_guidance_payload(snapshot) if snapshot else {}
        draft = await generate_research_draft(
            conversation_title=conversation.title,
            transcript=self._build_transcript(conversation_id),
            guidance=guidance,
        )
        sections = list(guidance.get("sections") or [])
        if not any(section.get("key") == "draft" for section in sections):
            sections.append(
                {
                    "key": "draft",
                    "title": "研究草案",
                    "style": "info",
                    "text": draft.get("title") or draft.get("topic") or "已生成研究草案",
                    "items": draft.get("next_actions", [])[:4],
                }
            )
        updated = memory_store.upsert_guidance_snapshot(
            conversation_id,
            status="draft_ready",
            headline=str(guidance.get("headline") or "已生成研究草案"),
            sections=sections,
            draft=draft,
            source_message_id=str(guidance.get("source_message_id") or ""),
        )
        payload = memory_store.as_guidance_payload(updated)
        memory_store.append_realtime_event(
            conversation_id=conversation_id,
            event_type="draft_generated",
            payload=payload,
        )
        return payload

    async def stream_reply(
        self,
        *,
        user_id: str,
        conversation_id: str,
        content: str,
        client_message_id: str | None,
    ) -> AsyncIterator[str]:
        conversation = self._require_conversation(user_id, conversation_id)

        memory_store.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            message_type="chat",
            content=content,
        )
        memory_store.append_realtime_event(
            conversation_id=conversation_id,
            event_type="message_started",
            payload={"client_message_id": client_message_id, "content": content},
        )

        accumulated = ""
        yield encode_sse(
            "message.started",
            {
                "conversation_id": conversation_id,
                "client_message_id": client_message_id,
            },
        )
        yield encode_sse("ping", {"ts": now_iso()})

        try:
            async for part in self.graph.astream(
                {
                    "conversation_id": conversation_id,
                    "user_input": content,
                    "recent_messages": self._build_recent_window(conversation_id, exclude_last=1),
                    "response_text": "",
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
            memory_store.append_realtime_event(
                conversation_id=conversation_id,
                event_type="message_failed",
                payload={"message": str(exc)},
            )
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
            memory_store.append_realtime_event(
                conversation_id=conversation_id,
                event_type="message_failed",
                payload={"message": "模型未返回有效内容"},
            )
            yield encode_sse(
                "message.failed",
                {
                    "code": "CHAT_STREAM_FAILED",
                    "message": "模型未返回有效内容",
                },
            )
            return

        assistant_message = memory_store.add_message(
            conversation_id=conversation_id,
            user_id=None,
            role="assistant",
            message_type="chat",
            content=final_text,
            metadata={},
        )
        latest_conversation = memory_store.increment_completed_turn(conversation_id) or conversation
        completed_payload = {
            "message": memory_store.as_message_payload(assistant_message),
            "conversation": memory_store.as_conversation_payload(latest_conversation),
        }
        memory_store.append_realtime_event(
            conversation_id=conversation_id,
            event_type="message_completed",
            payload=completed_payload,
        )
        yield encode_sse("message.completed", completed_payload)

        try:
            guidance_payload = await self._refresh_guidance(
                conversation_id=conversation_id,
                source_message_id=assistant_message.id,
            )
            refreshed_conversation = memory_store.get_conversation(conversation_id)
            if refreshed_conversation is not None and refreshed_conversation.title != latest_conversation.title:
                yield encode_sse(
                    "message.info",
                    {"detail": "已根据当前对话自动生成会话标题"},
                )
            yield encode_sse(
                "guidance.updated",
                {
                    "guidance": guidance_payload,
                    "conversation": memory_store.as_conversation_payload(refreshed_conversation)
                    if refreshed_conversation is not None
                    else None,
                },
            )
        except Exception as exc:
            memory_store.append_realtime_event(
                conversation_id=conversation_id,
                event_type="guidance_failed",
                payload={"message": str(exc)},
            )
            yield encode_sse("message.info", {"detail": f"专业提示区更新失败：{exc}"})


chat_service = ChatService()
