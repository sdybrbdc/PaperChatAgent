from __future__ import annotations

from typing import Any

from paperchat.agents.research_orchestrator.runtime_support import ResearchRunContext
from paperchat.agents.research_orchestrator.state_models import ExecutionState, PaperAgentState
from paperchat.agents.research_orchestrator.sub_writing_agent import (
    run_parallel_writing,
    run_retrieval,
    run_review,
    run_writing_director,
)


async def writing_node(
    state: PaperAgentState,
    *,
    model_slot: str = "conversation_model",
    context: ResearchRunContext | None = None,
) -> dict[str, Any]:
    state.current_step = ExecutionState.WRITING

    if context:
        context.start_node("writing.writing_director", detail="正在生成报告大纲", input_json=state.analyse_results)
    sections = await run_writing_director(
        user_request=state.user_request,
        analysis=state.analyse_results,
        model_slot=model_slot,
    )
    state.outline = sections
    if context:
        context.complete_node(
            "writing.writing_director",
            detail=f"写作规划完成，共 {len(sections)} 个章节",
            output_json={"sections": sections},
        )

    if context:
        context.start_node("writing.retrieval", detail="记录检索增强缺失工具", input_json={"sections": sections})
    retrieval = await run_retrieval(user_request=state.user_request, sections=sections, analysis=state.analyse_results)
    state.retrieval_results = retrieval
    for tool in retrieval.get("missing_tools", []):
        if tool not in state.missing_tools:
            state.missing_tools.append(tool)
    for capability in retrieval.get("skipped_capabilities", []):
        if capability not in state.skipped_capabilities:
            state.skipped_capabilities.append(capability)
    if context:
        context.complete_node("writing.retrieval", detail="检索增强暂未接入，已记录缺失工具", output_json=retrieval)

    if context:
        context.start_node("writing.parallel_writing", detail="正在并行生成章节草稿", input_json={"sections": sections})
    writted_sections = await run_parallel_writing(
        user_request=state.user_request,
        sections=sections,
        analysis=state.analyse_results,
        retrieval=retrieval,
        model_slot=model_slot,
    )
    state.writted_sections = writted_sections
    if context:
        context.complete_node(
            "writing.parallel_writing",
            detail=f"章节写作完成，共 {len(writted_sections)} 个章节",
            output_json={"sections": writted_sections},
        )

    if context:
        context.start_node("writing.review", detail="正在审查章节质量", input_json={"section_count": len(writted_sections)})
    review = await run_review(sections=writted_sections, analysis=state.analyse_results, model_slot=model_slot)
    state.review_result = review
    if context:
        context.complete_node("writing.review", detail="章节审查完成", output_json=review)

    return {
        "detail": "写作节点完成",
        "output": {
            "outline": sections,
            "writted_sections": writted_sections,
            "retrieval": retrieval,
            "review": review,
            "missing_tools": state.missing_tools,
            "skipped_capabilities": state.skipped_capabilities,
        },
    }
