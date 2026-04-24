from __future__ import annotations

from typing import Any

from paperchat.agents.research_orchestrator.runtime_support import (
    call_autogen_agent,
    compact_json,
    extract_json_object,
)
from paperchat.prompts.research_orchestrator import REVIEW_AGENT_PROMPT


async def run_review(
    *,
    sections: list[str],
    analysis: dict[str, Any],
    model_slot: str = "conversation_model",
) -> dict[str, Any]:
    prompt = f"""
章节草稿：
{compact_json(sections, limit=10000)}

分析依据：
{compact_json(analysis, limit=5000)}
"""
    try:
        response = await call_autogen_agent(
            name="review_agent",
            system_prompt=REVIEW_AGENT_PROMPT,
            user_prompt=prompt,
            model_slot=model_slot,
        )
        data = extract_json_object(response)
        if isinstance(data, dict):
            return {
                "approved": bool(data.get("approved", False)),
                "issues": data.get("issues") or [],
                "suggestions": data.get("suggestions") or [],
                "raw": response,
            }
    except Exception as exc:
        return {
            "approved": True,
            "issues": [],
            "suggestions": [f"审查节点未能解析模型输出：{exc}"],
        }
    return {"approved": True, "issues": [], "suggestions": []}
