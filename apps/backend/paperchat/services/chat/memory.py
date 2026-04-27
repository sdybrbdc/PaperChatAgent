from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from paperchat.database.dao import memory_store
from paperchat.database.dao.memory_store import hash_value
from paperchat.prompts import (
    MEMORY_EXTRACTION_SYSTEM_PROMPT,
    MEMORY_SUMMARY_SYSTEM_PROMPT,
    build_memory_extraction_prompt,
    build_memory_summary_prompt,
)
from paperchat.providers import get_guidance_chat_model


SUMMARY_KEEP_RECENT_MESSAGES = 8
SUMMARY_MIN_TOTAL_MESSAGES = 14
SUMMARY_MIN_NEW_MESSAGES = 4
MAX_RELEVANT_USER_MEMORIES = 6
MAX_EXISTING_MEMORY_PROMPT_ITEMS = 10
ALLOWED_MEMORY_TYPES = {"preference", "goal", "constraint", "background", "identity"}
KEYWORD_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}")


def _extract_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("memory payload is not a JSON object")
    return payload


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _normalize_summary_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": str(payload.get("summary") or "").strip(),
        "key_points": _normalize_string_list(payload.get("key_points")),
        "user_preferences": _normalize_string_list(payload.get("user_preferences")),
        "open_questions": _normalize_string_list(payload.get("open_questions")),
    }


def _normalize_memory_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in payload.get("memories", []) if isinstance(payload.get("memories"), list) else []:
        if not isinstance(item, dict):
            continue
        memory_type = str(item.get("memory_type") or "preference").strip().lower()
        if memory_type not in ALLOWED_MEMORY_TYPES:
            memory_type = "preference"
        title = str(item.get("title") or "").strip()
        content = str(item.get("content") or "").strip()
        if not title or not content:
            continue
        try:
            confidence = int(item.get("confidence") or 0)
        except (TypeError, ValueError):
            confidence = 0
        confidence = max(0, min(confidence, 100))
        if confidence < 60:
            continue
        normalized.append(
            {
                "memory_type": memory_type,
                "title": title,
                "content": content,
                "tags": _normalize_string_list(item.get("tags")),
                "confidence": confidence,
            }
        )
    return normalized


def _format_transcript(messages: list[Any]) -> str:
    if not messages:
        return ""
    return "\n".join(f"{message.role}: {message.content}" for message in messages)


def _extract_keywords(text: str) -> set[str]:
    lowered = text.lower()
    return {match.group(0) for match in KEYWORD_RE.finditer(lowered)}


def _memory_score(query: str, memory: dict[str, Any]) -> float:
    query_keywords = _extract_keywords(query)
    haystack = " ".join(
        [
            str(memory.get("memory_type") or ""),
            str(memory.get("title") or ""),
            str(memory.get("content") or ""),
            " ".join(str(tag) for tag in memory.get("tags") or []),
        ]
    ).lower()
    memory_keywords = _extract_keywords(haystack)
    overlap = len(query_keywords & memory_keywords)
    substring_bonus = sum(1 for token in query_keywords if len(token) >= 2 and token in haystack)
    return overlap * 4 + substring_bonus * 2 + float(memory.get("confidence") or 0) / 100.0


class ChatMemoryService:
    async def build_chat_memory_context(
        self,
        *,
        user_id: str,
        conversation_id: str,
        user_input: str,
        conversation_title: str,
    ) -> dict[str, Any]:
        conversation_memory = await self.maybe_refresh_conversation_summary(
            conversation_id=conversation_id,
            conversation_title=conversation_title,
        )
        if conversation_memory is None:
            stored_conversation_memory = memory_store.get_conversation_memory(conversation_id)
            conversation_memory = (
                memory_store.as_conversation_memory_payload(stored_conversation_memory)
                if stored_conversation_memory is not None
                else None
            )
        return {
            "conversation_memory": conversation_memory,
            "user_memories": self.get_relevant_user_memories(user_id=user_id, query=user_input),
        }

    async def maybe_refresh_conversation_summary(
        self,
        *,
        conversation_id: str,
        conversation_title: str,
        source_message_id: str | None = None,
    ) -> dict[str, Any] | None:
        messages = memory_store.list_messages(conversation_id)
        record = memory_store.get_conversation_memory(conversation_id)
        existing = memory_store.as_conversation_memory_payload(record) if record is not None else None

        if len(messages) < SUMMARY_MIN_TOTAL_MESSAGES:
            return existing

        compress_until = max(0, len(messages) - SUMMARY_KEEP_RECENT_MESSAGES)
        if compress_until <= 0:
            return existing

        compressed_message_count = int(existing.get("compressed_message_count") or 0) if existing else 0
        if compress_until - compressed_message_count < SUMMARY_MIN_NEW_MESSAGES:
            return existing

        transcript = _format_transcript(messages[compressed_message_count:compress_until])
        if not transcript.strip():
            return existing

        model = get_guidance_chat_model()
        prompt = build_memory_summary_prompt(
            conversation_title=conversation_title,
            existing_summary=existing,
            transcript=transcript,
            compressed_message_count=compressed_message_count,
        )
        response = await model.ainvoke(
            [
                SystemMessage(content=MEMORY_SUMMARY_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        normalized = _normalize_summary_payload(_extract_json_object(str(response.content)))
        updated = memory_store.upsert_conversation_memory(
            conversation_id,
            summary_text=normalized["summary"],
            key_points=normalized["key_points"],
            user_preferences=normalized["user_preferences"],
            open_questions=normalized["open_questions"],
            compressed_message_count=compress_until,
            source_message_id=source_message_id,
        )
        return memory_store.as_conversation_memory_payload(updated)

    def get_relevant_user_memories(self, *, user_id: str, query: str, limit: int = MAX_RELEVANT_USER_MEMORIES) -> list[dict[str, Any]]:
        memories = [memory_store.as_user_memory_payload(item) for item in memory_store.list_user_memories(user_id)]
        active_memories = [item for item in memories if item.get("active", True)]
        if not active_memories:
            return []

        scored = sorted(
            active_memories,
            key=lambda item: (_memory_score(query, item), item.get("last_observed_at") or ""),
            reverse=True,
        )
        relevant = [item for item in scored if _memory_score(query, item) > 0]
        if relevant:
            return relevant[:limit]
        return scored[: min(limit, 3)]

    async def remember_latest_turn(
        self,
        *,
        user_id: str,
        conversation_id: str,
        conversation_title: str,
        source_message_id: str | None = None,
    ) -> list[dict[str, Any]]:
        messages = memory_store.get_recent_context_messages(conversation_id, 6)
        transcript = _format_transcript(messages)
        if not transcript.strip():
            return []

        existing_memories = self.get_relevant_user_memories(
            user_id=user_id,
            query=transcript,
            limit=MAX_EXISTING_MEMORY_PROMPT_ITEMS,
        )
        model = get_guidance_chat_model()
        prompt = build_memory_extraction_prompt(
            conversation_title=conversation_title,
            transcript=transcript,
            existing_memories=existing_memories,
        )
        response = await model.ainvoke(
            [
                SystemMessage(content=MEMORY_EXTRACTION_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        items = _normalize_memory_items(_extract_json_object(str(response.content)))
        stored: list[dict[str, Any]] = []
        for item in items:
            fingerprint = hash_value(
                f"{item['memory_type'].strip().lower()}|{item['title'].strip().lower()}|{item['content'].strip().lower()}"
            )
            record = memory_store.upsert_user_memory(
                user_id=user_id,
                memory_type=item["memory_type"],
                title=item["title"],
                content=item["content"],
                tags=item["tags"],
                confidence=item["confidence"],
                memory_fingerprint=fingerprint,
                source_conversation_id=conversation_id,
                source_message_id=source_message_id,
            )
            stored.append(memory_store.as_user_memory_payload(record))
        return stored


chat_memory_service = ChatMemoryService()
