from __future__ import annotations

import re

from paperchat.agents.research_orchestrator.runtime_support import call_autogen_agent, compact_json
from paperchat.prompts.research_orchestrator import WRITING_DIRECTOR_AGENT_PROMPT


def parse_outline(outline_text: str) -> list[str]:
    lines = [line.strip() for line in outline_text.splitlines() if line.strip()]
    sections = [line for line in lines if re.match(r"^\[?\d+(?:\.\d+)?\]?\s+", line)]
    if sections:
        return sections
    chunks = [chunk.strip(" -\t") for chunk in re.split(r"[;\n]", outline_text) if chunk.strip()]
    return chunks[:7]


async def run_writing_director(
    *,
    user_request: str,
    analysis: dict,
    model_slot: str = "conversation_model",
) -> list[str]:
    prompt = f"""
用户需求：
{user_request}

分析材料：
{compact_json(analysis, limit=10000)}
"""
    try:
        response = await call_autogen_agent(
            name="writing_director_agent",
            system_prompt=WRITING_DIRECTOR_AGENT_PROMPT,
            user_prompt=prompt,
            model_slot=model_slot,
        )
        sections = parse_outline(response)
    except Exception:
        sections = []
    if not sections:
        sections = [
            "1 研究背景与问题定义 (说明研究方向、应用背景和关键问题)",
            "2 代表性论文与方法分类 (按主题梳理代表论文及技术路线)",
            "3 技术趋势与方法对比 (比较不同路线的优势、局限和适用场景)",
            "4 局限性与未来方向 (总结挑战并提出后续研究建议)",
        ]
    return sections[:7]
