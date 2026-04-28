from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from paperchat.api.errcode import AppError
from paperchat.api.responses.sse import encode_sse, now_iso
from paperchat.database.dao import memory_store
from paperchat.prompts import CHAT_CONTEXT_LOADING_MESSAGE, CHAT_READY_MESSAGE, build_chat_system_prompt
from paperchat.providers import get_conversation_chat_model, get_tool_call_chat_model
from paperchat.services.capabilities import capability_service
from paperchat.services.chat.memory import chat_memory_service
from paperchat.services.stream import normalize_chat_stream_part, translate_chat_stream_part
from paperchat.workflows.chat_graph import build_chat_graph, should_start_research_tool
from paperchat.workflows.guidance_graph import generate_guidance_analysis, generate_research_draft


class ChatService:
    def __init__(self) -> None:
        self.graph = build_chat_graph()

    TOOL_RESULT_CHAR_LIMIT = 7000
    MAX_TOOL_CALLS = 3
    LARK_SKILL_KEYWORDS: dict[str, tuple[str, ...]] = {
        "lark-doc": ("文档", "云文档", "云空间", "文件", "资料", "搜索", "查找", "doc", "docs"),
        "lark-wiki": ("知识库", "wiki", "空间", "节点"),
        "lark-drive": ("云空间", "文件", "文件夹", "上传", "下载", "权限", "评论"),
        "lark-sheets": ("电子表格", "表格", "sheet", "spreadsheet"),
        "lark-base": ("多维表格", "base", "bitable", "数据表"),
        "lark-calendar": ("日历", "日程", "会议", "空闲", "会议室"),
        "lark-im": ("消息", "群", "聊天", "会话", "im"),
        "lark-mail": ("邮件", "邮箱", "草稿", "收件箱", "mail"),
        "lark-task": ("任务", "待办", "清单", "todo"),
        "lark-contact": ("联系人", "通讯录", "同事", "部门"),
        "lark-minutes": ("妙记", "minutes"),
        "lark-vc": ("视频会议", "会议记录", "会议纪要", "vc"),
        "lark-whiteboard": ("画板", "白板", "流程图", "架构图", "mermaid"),
    }

    @staticmethod
    def _chunk_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, dict):
                    text = item.get("text") or item.get("content") or ""
                    if text:
                        parts.append(str(text))
                    continue
                text = getattr(item, "text", "") or getattr(item, "content", "")
                if text:
                    parts.append(str(text))
            return "".join(parts)
        text = getattr(content, "text", "") or getattr(content, "content", "")
        if text:
            return str(text)
        return str(content) if content else ""

    def _safe_json_dumps(self, value: Any, *, limit: int | None = None) -> str:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except TypeError:
            text = str(value)
        if limit and len(text) > limit:
            return text[:limit] + "\n[内容过长，已截断]"
        return text

    def _parse_json_object(self, text: str) -> dict[str, Any]:
        clean = text.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean).strip()
        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", clean, flags=re.S)
            if not match:
                return {}
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
        return data if isinstance(data, dict) else {}

    def _available_chat_capabilities(self, user_id: str) -> list[dict[str, Any]]:
        payload = capability_service.list_capabilities_payload(user_id=user_id)
        items = payload.get("items", [])
        available_statuses = {"available", "enabled", "active"}
        capabilities: list[dict[str, Any]] = []
        for item in items:
            if item.get("kind") not in {"rag", "skill", "mcp"}:
                continue
            status = str(item.get("status") or "")
            if status not in available_statuses:
                continue
            capabilities.append(
                {
                    "key": item.get("key"),
                    "kind": item.get("kind"),
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "input_schema": item.get("input_schema") or {},
                    "trigger_phrases": (item.get("metadata") or {}).get("trigger_phrases") or [],
                }
            )
        return capabilities

    def _skill_trigger_match_reason(self, *, capability: dict[str, Any], user_input: str) -> str:
        if capability.get("kind") != "skill":
            return ""
        lark_reason = self._lark_skill_match_reason(capability=capability, user_input=user_input)
        if lark_reason:
            return lark_reason
        normalized_input = user_input.lower()
        has_skill_intent = any(
            token in normalized_input or token in user_input
            for token in ("skill", "skills", "技能", "使用", "调用", "加载", "启用", "按", "用")
        )
        raw_phrases = [
            str(capability.get("name") or ""),
            *[str(item) for item in capability.get("trigger_phrases") or []],
        ]
        phrases: list[str] = []
        for phrase in raw_phrases:
            clean = phrase.strip()
            if clean and clean not in phrases:
                phrases.append(clean)
        for phrase in phrases:
            lower_phrase = phrase.lower()
            explicit_markers = (f"${phrase}", f"@{phrase}", f"${lower_phrase}", f"@{lower_phrase}")
            if any(marker in user_input or marker in normalized_input for marker in explicit_markers):
                return f"用户明确点名 {phrase}"
            if lower_phrase and lower_phrase in normalized_input:
                has_cjk = any("\u4e00" <= char <= "\u9fff" for char in phrase)
                strong_phrase = len(phrase) >= 6 or (has_cjk and len(phrase) >= 3)
                if has_skill_intent or strong_phrase:
                    return f"用户消息匹配 Skill 触发词：{phrase}"
        return ""

    def _lark_skill_match_reason(self, *, capability: dict[str, Any], user_input: str) -> str:
        name = str(capability.get("name") or "").lower()
        if not name.startswith("lark-"):
            return ""
        normalized_input = user_input.lower()
        if not any(token in normalized_input or token in user_input for token in ("lark", "feishu", "飞书")):
            return ""
        for keyword in self.LARK_SKILL_KEYWORDS.get(name, ()):
            if keyword.lower() in normalized_input or keyword in user_input:
                return f"用户消息匹配飞书 {name} 场景：{keyword}"
        return ""

    def _deterministic_skill_calls(
        self,
        *,
        capabilities: list[dict[str, Any]],
        user_input: str,
    ) -> list[dict[str, Any]]:
        calls: list[dict[str, Any]] = []
        for capability in capabilities:
            reason = self._skill_trigger_match_reason(capability=capability, user_input=user_input)
            if not reason:
                continue
            calls.append(
                {
                    "capability_key": capability["key"],
                    "input": {
                        "instruction": f"按 {capability.get('name') or capability['key']} Skill 的 SKILL.md 指令处理本轮请求。",
                        "user_input": user_input,
                    },
                    "reason": reason,
                }
            )
            if len(calls) >= self.MAX_TOOL_CALLS:
                break
        return calls

    async def _select_chat_capability_calls(
        self,
        *,
        user_id: str,
        user_input: str,
        conversation_id: str,
    ) -> list[dict[str, Any]]:
        capabilities = self._available_chat_capabilities(user_id)
        if not capabilities:
            return []
        deterministic_calls = self._deterministic_skill_calls(capabilities=capabilities, user_input=user_input)

        selector_prompt = (
            "你是 PaperChatAgent 的能力路由器。根据用户本轮消息，从可用能力中选择是否需要调用工具。"
            "\n只返回严格 JSON，不要 Markdown。格式："
            '{"calls":[{"capability_key":"...","input":{},"reason":"..."}]}'
            "\n规则："
            "\n1. 不需要工具时返回 {\"calls\":[]}。"
            f"\n2. 最多选择 {self.MAX_TOOL_CALLS} 个能力。"
            "\n3. rag.retrieve 用于检索项目知识库，input 形如 {\"query\":\"...\",\"top_k\":6}。"
            "\n4. skill.* 用于加载真实 SKILL.md 指令上下文，input 形如 {\"instruction\":\"...\",\"user_input\":\"...\"}。"
            "\n5. mcp.* 只有在参数能从用户消息中明确推出时才调用，input 必须匹配该工具的 input_schema。"
            "\n6. 删除、发送、写入、修改类 MCP 工具只有在用户明确要求时才调用。"
            "\n7. 飞书/Lark 场景优先选择最具体的 lark-* Skill；云文档/云空间资源发现优先选择 lark-doc。"
            "\n8. lark-openapi-explorer 只在现有 lark-* Skill 无法覆盖需求时选择。"
        )
        model = get_tool_call_chat_model()
        try:
            response = await model.ainvoke(
                [
                    SystemMessage(content=selector_prompt),
                    HumanMessage(
                        content=(
                            "可用能力：\n"
                            + self._safe_json_dumps(capabilities, limit=16000)
                            + "\n\n"
                            + f"conversation_id: {conversation_id}\n"
                            + f"用户消息：{user_input}"
                        )
                    ),
                ]
            )
        except Exception:
            return deterministic_calls

        parsed = self._parse_json_object(self._chunk_to_text(getattr(response, "content", "")))
        calls = parsed.get("calls") if isinstance(parsed, dict) else []
        if not isinstance(calls, list):
            return deterministic_calls

        capability_keys = {str(item.get("key")) for item in capabilities}
        selected: list[dict[str, Any]] = []
        seen: set[str] = set()
        for call in deterministic_calls:
            capability_key = str(call.get("capability_key") or "")
            if capability_key not in capability_keys or capability_key in seen:
                continue
            selected.append(call)
            seen.add(capability_key)
        for call in calls:
            if not isinstance(call, dict):
                continue
            capability_key = str(call.get("capability_key") or "")
            if capability_key not in capability_keys or capability_key in seen:
                continue
            input_payload = call.get("input") if isinstance(call.get("input"), dict) else {}
            selected.append(
                {
                    "capability_key": capability_key,
                    "input": input_payload,
                    "reason": str(call.get("reason") or ""),
                }
            )
            seen.add(capability_key)
            if len(selected) >= self.MAX_TOOL_CALLS:
                break
        return selected

    def _tool_result_summary(self, result: dict[str, Any]) -> str:
        output = result.get("result", result)
        if isinstance(output, dict):
            for key in ("text", "message"):
                value = output.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()[:600]
            nested = output.get("result")
            if isinstance(nested, dict):
                text = nested.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()[:600]
        return self._safe_json_dumps(output, limit=600)

    def _format_tool_context(self, tool_results: list[dict[str, Any]]) -> str:
        if not tool_results:
            return ""
        lines = [
            "## 已调用能力结果",
            "以下内容来自系统在本轮回复前调用的 RAG、Skill 或 MCP 能力。请基于这些结果回答；如果工具失败，说明失败并继续给出可行替代。",
        ]
        for index, item in enumerate(tool_results, start=1):
            lines.append(f"\n### {index}. {item['name']} ({item['kind']})")
            if item.get("reason"):
                lines.append(f"调用原因：{item['reason']}")
            if item.get("status") == "failed":
                lines.append(f"调用失败：{item.get('error')}")
                continue
            lines.append(self._safe_json_dumps(item.get("result"), limit=self.TOOL_RESULT_CHAR_LIMIT))
        return "\n".join(lines)

    def _public_tool_calls(self, tool_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "capability_key": item.get("capability_key"),
                "kind": item.get("kind"),
                "name": item.get("name"),
                "reason": item.get("reason"),
                "status": item.get("status"),
                "summary": item.get("summary", ""),
            }
            for item in tool_results
        ]

    async def _execute_selected_capabilities(
        self,
        *,
        user_id: str,
        conversation_id: str,
        user_input: str,
    ) -> list[dict[str, Any]]:
        selected_calls = await self._select_chat_capability_calls(
            user_id=user_id,
            user_input=user_input,
            conversation_id=conversation_id,
        )
        tool_results: list[dict[str, Any]] = []
        for call in selected_calls:
            capability_key = call["capability_key"]
            capability = capability_service.get_capability_payload(user_id=user_id, capability_key=capability_key)
            tool_item = {
                "capability_key": capability_key,
                "kind": capability.get("kind"),
                "name": capability.get("name") or capability_key,
                "reason": call.get("reason", ""),
                "input": call.get("input", {}),
                "status": "running",
            }
            try:
                result = await capability_service.execute_capability_payload(
                    user_id=user_id,
                    capability_key=capability_key,
                    input_payload=dict(call.get("input") or {}),
                    context={"conversation_id": conversation_id, "source": "chat"},
                    dry_run=False,
                )
                tool_item["status"] = "succeeded"
                tool_item["result"] = result.get("result")
                tool_item["summary"] = self._tool_result_summary(result)
            except Exception as exc:
                tool_item["status"] = "failed"
                tool_item["error"] = str(exc)
                tool_item["summary"] = str(exc)
            tool_results.append(tool_item)
        return tool_results

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
                    "title": "研究方案",
                    "style": "draft_entry",
                    "text": "当前信息已基本收敛，可以手动生成研究方案。",
                    "items": [],
                }
            )

        if status == "draft_ready" and draft:
            sections.append(
                {
                    "key": "draft",
                    "title": "研究方案",
                    "style": "info",
                    "text": draft.get("title") or draft.get("topic") or "已生成研究方案",
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
                    "title": "研究方案",
                    "style": "info",
                    "text": draft.get("title") or draft.get("topic") or "已生成研究方案",
                    "items": draft.get("next_actions", [])[:4],
                }
            )
        updated = memory_store.upsert_guidance_snapshot(
            conversation_id,
            status="draft_ready",
            headline=str(guidance.get("headline") or "已生成研究方案"),
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

        user_message = memory_store.add_message(
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

        conversation_memory = None
        user_memories: list[dict[str, Any]] = []
        tool_results: list[dict[str, Any]] = []
        try:
            memory_context = await chat_memory_service.build_chat_memory_context(
                user_id=user_id,
                conversation_id=conversation_id,
                user_input=content,
                conversation_title=conversation.title,
            )
            conversation_memory = memory_context.get("conversation_memory")
            user_memories = list(memory_context.get("user_memories") or [])
        except Exception as exc:
            memory_store.append_realtime_event(
                conversation_id=conversation_id,
                event_type="memory_context_failed",
                payload={"message": str(exc), "user_message_id": user_message.id},
            )

        if should_start_research_tool(content):
            fallback_response_text = ""
            try:
                async for part in self.graph.astream(
                    {
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                        "user_input": content,
                        "recent_messages": self._build_recent_window(conversation_id, limit=8, exclude_last=1),
                        "conversation_memory": conversation_memory,
                        "user_memories": user_memories,
                        "response_text": "",
                    },
                    stream_mode=["messages", "updates", "custom"],
                ):
                    normalized_part = normalize_chat_stream_part(part)
                    if normalized_part.get("type") == "updates":
                        for node_update in normalized_part.get("data", {}).values():
                            if isinstance(node_update, dict) and node_update.get("response_text"):
                                fallback_response_text = str(node_update["response_text"])
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

            if not accumulated.strip() and fallback_response_text.strip():
                accumulated = fallback_response_text
                yield encode_sse(
                    "message.delta",
                    {
                        "delta": fallback_response_text,
                        "accumulated": fallback_response_text,
                    },
                )
        else:
            if conversation_memory and conversation_memory.get("summary"):
                yield encode_sse("message.info", {"detail": "已载入短期会话记忆摘要"})
            if user_memories:
                yield encode_sse("message.info", {"detail": f"已载入 {len(user_memories)} 条用户长期记忆"})
            yield encode_sse(
                "message.progress",
                {
                    "stage": "load_memory",
                    "node": "load_memory",
                    "status": "completed",
                    "detail": "记忆上下文已加载",
                },
            )
            yield encode_sse("message.info", {"detail": CHAT_CONTEXT_LOADING_MESSAGE})
            yield encode_sse("message.info", {"detail": CHAT_READY_MESSAGE})
            yield encode_sse(
                "message.progress",
                {
                    "stage": "load_context",
                    "node": "load_context",
                    "status": "completed",
                    "detail": "会话上下文已加载",
                },
            )
            yield encode_sse(
                "message.progress",
                {
                    "stage": "route_capabilities",
                    "node": "route_capabilities",
                    "status": "running",
                    "detail": "正在判断是否需要使用知识库、Skills 或 MCP",
                },
            )
            tool_results = await self._execute_selected_capabilities(
                user_id=user_id,
                conversation_id=conversation_id,
                user_input=content,
            )
            for tool_result in tool_results:
                yield encode_sse(
                    "message.tool",
                    {
                        "capability_key": tool_result.get("capability_key"),
                        "kind": tool_result.get("kind"),
                        "name": tool_result.get("name"),
                        "reason": tool_result.get("reason"),
                        "status": tool_result.get("status"),
                        "summary": tool_result.get("summary", ""),
                    },
                )
            yield encode_sse(
                "message.progress",
                {
                    "stage": "route_capabilities",
                    "node": "route_capabilities",
                    "status": "completed",
                    "detail": f"能力调用完成：{len(tool_results)} 个",
                },
            )

            model = get_conversation_chat_model()
            tool_context = self._format_tool_context(tool_results)
            prompt_messages: list[BaseMessage] = [
                SystemMessage(
                    content=build_chat_system_prompt(
                        conversation_memory=conversation_memory,
                        user_memories=user_memories,
                    )
                ),
            ]
            if tool_context:
                prompt_messages.append(SystemMessage(content=tool_context))
            prompt_messages.extend(self._build_recent_window(conversation_id, limit=8, exclude_last=1))
            prompt_messages.append(HumanMessage(content=content))
            try:
                async for response_chunk in model.astream(prompt_messages):
                    delta = self._chunk_to_text(getattr(response_chunk, "content", ""))
                    if not delta:
                        continue
                    accumulated += delta
                    yield encode_sse(
                        "message.delta",
                        {
                            "delta": delta,
                            "accumulated": accumulated,
                        },
                    )
                yield encode_sse(
                    "message.progress",
                    {
                        "stage": "call_model",
                        "node": "call_model",
                        "status": "completed",
                        "detail": "模型生成阶段已完成",
                    },
                )
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
            metadata={"tool_calls": self._public_tool_calls(tool_results)} if tool_results else {},
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

        current_conversation = memory_store.get_conversation(conversation_id) or conversation
        try:
            stored_memories = await chat_memory_service.remember_latest_turn(
                user_id=user_id,
                conversation_id=conversation_id,
                conversation_title=current_conversation.title,
                source_message_id=assistant_message.id,
            )
            refreshed_summary = await chat_memory_service.maybe_refresh_conversation_summary(
                conversation_id=conversation_id,
                conversation_title=current_conversation.title,
                source_message_id=assistant_message.id,
            )
            memory_store.append_realtime_event(
                conversation_id=conversation_id,
                event_type="memory_updated",
                payload={
                    "stored_count": len(stored_memories),
                    "has_summary": bool(refreshed_summary and refreshed_summary.get("summary")),
                    "source_message_id": assistant_message.id,
                },
            )
        except Exception as exc:
            memory_store.append_realtime_event(
                conversation_id=conversation_id,
                event_type="memory_failed",
                payload={"message": str(exc), "source_message_id": assistant_message.id},
            )


chat_service = ChatService()
