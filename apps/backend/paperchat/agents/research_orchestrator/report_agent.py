from __future__ import annotations

from typing import Any

from paperchat.agents.research_orchestrator.runtime_support import (
    call_autogen_agent,
    compact_json,
    summarize_text,
)
from paperchat.agents.research_orchestrator.state_models import ExecutionState, PaperAgentState
from paperchat.prompts.research_orchestrator import REPORT_AGENT_PROMPT


async def report_node(
    state: PaperAgentState,
    *,
    model_slot: str = "conversation_model",
) -> dict[str, Any]:
    state.current_step = ExecutionState.REPORTING
    prompt = f"""
用户需求：
{state.user_request}

章节内容：
{compact_json(state.writted_sections, limit=14000)}

审查结果：
{compact_json(state.review_result, limit=3000)}

缺失工具记录：
{compact_json({"missing_tools": state.missing_tools, "skipped_capabilities": state.skipped_capabilities}, limit=2000)}
"""
    try:
        markdown = await call_autogen_agent(
            name="report_agent",
            system_prompt=REPORT_AGENT_PROMPT,
            user_prompt=prompt,
            model_slot=model_slot,
        )
    except Exception:
        markdown = "\n\n".join(state.writted_sections)
    if not markdown.strip():
        markdown = "\n\n".join(state.writted_sections)
    state.report_markdown = markdown
    state.report_summary = summarize_text(markdown, limit=220)
    return {
        "detail": "报告生成完成",
        "output": {
            "report_markdown": markdown,
            "summary": state.report_summary,
            "missing_tools": state.missing_tools,
            "skipped_capabilities": state.skipped_capabilities,
        },
    }
