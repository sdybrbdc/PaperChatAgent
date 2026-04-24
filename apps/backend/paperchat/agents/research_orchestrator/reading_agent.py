from __future__ import annotations

from typing import Any

from paperchat.agents.research_orchestrator.runtime_support import (
    call_autogen_agent,
    compact_json,
    extract_json_object,
    gather_limited,
    summarize_text,
)
from paperchat.agents.research_orchestrator.state_models import (
    ExecutionState,
    ExtractedPaperData,
    ExtractedPapersData,
    KeyMethodology,
    PaperAgentState,
)
from paperchat.prompts.research_orchestrator import READING_AGENT_PROMPT


def _fallback_extract(paper: dict[str, Any]) -> ExtractedPaperData:
    summary = str(paper.get("summary") or "")
    return ExtractedPaperData(
        paper_id=str(paper.get("paper_id") or ""),
        title=str(paper.get("title") or ""),
        core_problem=summarize_text(summary, limit=420),
        key_methodology=KeyMethodology(name="未明确声明", principle=summarize_text(summary, limit=260), novelty="未明确声明"),
        datasets_used=[],
        evaluation_metrics=[],
        main_results="摘要中未提供可核实的主结果数值",
        limitations="摘要中未明确说明局限性",
        contributions=[summarize_text(summary, limit=280)] if summary else [],
        source_url=str(paper.get("url") or ""),
    )


async def _extract_one(paper: dict[str, Any], *, model_slot: str) -> ExtractedPaperData:
    prompt = f"""
请抽取以下论文信息：
{compact_json(paper, limit=5000)}
"""
    try:
        response = await call_autogen_agent(
            name="reading_agent",
            system_prompt=READING_AGENT_PROMPT,
            user_prompt=prompt,
            model_slot=model_slot,
        )
        data = extract_json_object(response)
        if isinstance(data, dict) and "papers" in data and isinstance(data["papers"], list) and data["papers"]:
            data = data["papers"][0]
        if isinstance(data, list) and data:
            data = data[0]
        extracted = ExtractedPaperData.model_validate(data)
        extracted.paper_id = extracted.paper_id or str(paper.get("paper_id") or "")
        extracted.title = extracted.title or str(paper.get("title") or "")
        extracted.source_url = extracted.source_url or str(paper.get("url") or "")
        return extracted
    except Exception:
        return _fallback_extract(paper)


async def reading_node(state: PaperAgentState, *, model_slot: str = "conversation_model") -> dict[str, Any]:
    state.current_step = ExecutionState.READING
    papers = state.search_results or []
    extracted = await gather_limited(
        4,
        [lambda paper=paper: _extract_one(paper, model_slot=model_slot) for paper in papers],
    )
    extracted_data = ExtractedPapersData(papers=extracted)
    state.extracted_data = extracted_data
    if "temporary_knowledge_base_write" not in state.missing_tools:
        state.missing_tools.append("temporary_knowledge_base_write")
    return {
        "detail": f"论文阅读完成，共抽取 {len(extracted_data.papers)} 篇论文",
        "output": {
            "papers": [paper.model_dump() for paper in extracted_data.papers],
            "missing_tools": ["temporary_knowledge_base_write"],
        },
    }
