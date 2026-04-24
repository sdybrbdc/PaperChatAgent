from __future__ import annotations

import asyncio
from typing import Any

from paperchat.agents.research_orchestrator.runtime_support import ResearchRunContext
from paperchat.agents.research_orchestrator.state_models import ExecutionState, PaperAgentState
from paperchat.agents.research_orchestrator.sub_analyse_agent import (
    run_cluster_analysis,
    run_deep_analysis,
    run_global_analysis,
)


async def analyse_node(
    state: PaperAgentState,
    *,
    model_slot: str = "reasoning_model",
    context: ResearchRunContext | None = None,
) -> dict[str, Any]:
    state.current_step = ExecutionState.ANALYZING

    if context:
        context.start_node("analyse.cluster", detail="正在进行论文主题聚类", input_json={"papers": len(state.extracted_data.papers)})
    clusters = await run_cluster_analysis(state.extracted_data, model_slot=model_slot)
    state.cluster_analysis = [cluster.to_dict() for cluster in clusters]
    if context:
        context.complete_node(
            "analyse.cluster",
            detail=f"聚类完成，共形成 {len(clusters)} 个主题",
            output_json={"clusters": state.cluster_analysis},
        )

    if context:
        context.start_node("analyse.deep_analyse", detail="正在进行主题深度分析", input_json={"clusters": len(clusters)})
    deep_results = await asyncio.gather(*[run_deep_analysis(cluster, model_slot=model_slot) for cluster in clusters])
    state.deep_analysis = [item.to_dict() for item in deep_results]
    if context:
        context.complete_node(
            "analyse.deep_analyse",
            detail="深度分析完成",
            output_json={"deep_analysis": state.deep_analysis},
        )

    if context:
        context.start_node("analyse.global_analyse", detail="正在生成全局洞察", input_json={"clusters": len(deep_results)})
    global_result = await run_global_analysis(deep_results, model_slot=model_slot)
    state.global_analysis = global_result
    state.analyse_results = {
        "cluster_analysis": state.cluster_analysis,
        "deep_analysis": state.deep_analysis,
        "global_analysis": global_result,
    }
    if context:
        context.complete_node(
            "analyse.global_analyse",
            detail="全局分析完成",
            output_json=global_result,
        )

    return {
        "detail": "分析节点完成",
        "output": state.analyse_results,
    }
