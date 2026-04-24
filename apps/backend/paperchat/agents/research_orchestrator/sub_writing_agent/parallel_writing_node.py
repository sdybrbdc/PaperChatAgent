from __future__ import annotations

import asyncio
from typing import Any

from paperchat.agents.research_orchestrator.runtime_support import call_autogen_agent, compact_json
from paperchat.prompts.research_orchestrator import WRITING_AGENT_PROMPT


async def _write_section(
    *,
    section: str,
    user_request: str,
    analysis: dict[str, Any],
    retrieval: dict[str, Any],
    model_slot: str,
) -> str:
    prompt = f"""
用户需求：
{user_request}

当前章节任务：
{section}

全局分析与证据：
{compact_json(analysis, limit=9000)}

检索增强上下文：
{compact_json(retrieval, limit=3000)}

请输出该章节正文，使用 Markdown 二级或三级标题。
"""
    return await call_autogen_agent(
        name="writing_agent",
        system_prompt=WRITING_AGENT_PROMPT,
        user_prompt=prompt,
        model_slot=model_slot,
    )


async def run_parallel_writing(
    *,
    user_request: str,
    sections: list[str],
    analysis: dict[str, Any],
    retrieval: dict[str, Any],
    model_slot: str = "conversation_model",
) -> list[str]:
    semaphore = asyncio.Semaphore(3)

    async def _run(section: str) -> str:
        async with semaphore:
            try:
                return await _write_section(
                    section=section,
                    user_request=user_request,
                    analysis=analysis,
                    retrieval=retrieval,
                    model_slot=model_slot,
                )
            except Exception as exc:
                return f"## {section}\n\n本章节生成失败：{exc}"

    return await asyncio.gather(*[_run(section) for section in sections])
