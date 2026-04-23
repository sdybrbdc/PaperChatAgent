from __future__ import annotations

import json
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from paperchat.prompts import DRAFT_SYSTEM_PROMPT, GUIDANCE_SYSTEM_PROMPT, build_draft_prompt, build_guidance_prompt
from paperchat.providers import get_guidance_chat_model


VALID_GUIDANCE_STATUSES = {"casual_chat", "topic_exploration", "needs_more_info", "ready_for_draft", "draft_ready"}


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
        raise ValueError("guidance payload is not a JSON object")
    return payload


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_guidance_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    recognized = payload.get("recognized") if isinstance(payload.get("recognized"), dict) else {}
    status = str(payload.get("status") or "casual_chat").strip()
    if status not in VALID_GUIDANCE_STATUSES:
        status = "casual_chat"
    return {
        "status": status,
        "headline": str(payload.get("headline") or "").strip(),
        "recognized": {
            "topic": str(recognized.get("topic") or "").strip(),
            "audience": str(recognized.get("audience") or "").strip(),
            "goal": str(recognized.get("goal") or "").strip(),
            "outputs": _normalize_string_list(recognized.get("outputs")),
            "materials": _normalize_string_list(recognized.get("materials")),
            "agents": _normalize_string_list(recognized.get("agents")),
        },
        "suggested_steps": _normalize_string_list(payload.get("suggested_steps")),
        "missing_info": _normalize_string_list(payload.get("missing_info")),
        "suggested_title": str(payload.get("suggested_title") or "").strip(),
    }


def _normalize_draft_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": str(payload.get("title") or "").strip(),
        "topic": str(payload.get("topic") or "").strip(),
        "objective": str(payload.get("objective") or "").strip(),
        "scope": str(payload.get("scope") or "").strip(),
        "suggested_materials": _normalize_string_list(payload.get("suggested_materials")),
        "suggested_agents": _normalize_string_list(payload.get("suggested_agents")),
        "next_actions": _normalize_string_list(payload.get("next_actions")),
    }


class GuidanceGraphState(TypedDict):
    conversation_title: str
    transcript: str
    existing_headline: str
    existing_draft: dict[str, Any] | None
    should_suggest_title: bool
    guidance_analysis: dict[str, Any]


def build_guidance_graph():
    model = get_guidance_chat_model()

    async def generate_guidance(state: GuidanceGraphState):
        prompt = build_guidance_prompt(
            conversation_title=state["conversation_title"],
            transcript=state["transcript"],
            existing_headline=state["existing_headline"],
            existing_draft=state["existing_draft"],
            should_suggest_title=state["should_suggest_title"],
        )
        response = await model.ainvoke(
            [
                SystemMessage(content=GUIDANCE_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        parsed = _extract_json_object(str(response.content))
        return {"guidance_analysis": _normalize_guidance_analysis(parsed)}

    graph = StateGraph(GuidanceGraphState)
    graph.add_node("generate_guidance", generate_guidance)
    graph.add_edge(START, "generate_guidance")
    graph.add_edge("generate_guidance", END)
    return graph.compile()


async def generate_guidance_analysis(
    *,
    conversation_title: str,
    transcript: str,
    existing_headline: str,
    existing_draft: dict[str, Any] | None,
    should_suggest_title: bool,
) -> dict[str, Any]:
    graph = build_guidance_graph()
    result = await graph.ainvoke(
        {
            "conversation_title": conversation_title,
            "transcript": transcript,
            "existing_headline": existing_headline,
            "existing_draft": existing_draft,
            "should_suggest_title": should_suggest_title,
            "guidance_analysis": {},
        }
    )
    return result["guidance_analysis"]


async def generate_research_draft(*, conversation_title: str, transcript: str, guidance: dict[str, Any]) -> dict[str, Any]:
    model = get_guidance_chat_model()
    prompt = build_draft_prompt(
        conversation_title=conversation_title,
        transcript=transcript,
        guidance=guidance,
    )
    response = await model.ainvoke(
        [
            SystemMessage(content=DRAFT_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
    )
    parsed = _extract_json_object(str(response.content))
    return _normalize_draft_payload(parsed)
