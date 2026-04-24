from __future__ import annotations

from typing import Any

from paperchat.agents.research_orchestrator.runtime_support import call_autogen_agent, compact_json
from paperchat.agents.research_orchestrator.sub_analyse_agent.deep_analyse_agent import DeepAnalyseResult
from paperchat.prompts.research_orchestrator import GLOBAL_ANALYSE_AGENT_PROMPT


async def run_global_analysis(
    deep_results: list[DeepAnalyseResult],
    *,
    model_slot: str = "reasoning_model",
) -> dict[str, Any]:
    cluster_summaries = [
        {
            "cluster_id": item.cluster_id,
            "theme": item.theme,
            "keywords": item.keywords,
            "paper_count": item.paper_count,
            "deep_analyse": item.deep_analyse,
        }
        for item in deep_results
    ]
    prompt = f"请基于以下主题簇深度分析生成全局分析：\n{compact_json(cluster_summaries, limit=12000)}"
    try:
        global_analyse = await call_autogen_agent(
            name="global_analyse_agent",
            system_prompt=GLOBAL_ANALYSE_AGENT_PROMPT,
            user_prompt=prompt,
            model_slot=model_slot,
            reasoning=True,
        )
    except Exception as exc:
        global_analyse = f"全局分析失败：{exc}"
    return {
        "total_clusters": len(deep_results),
        "total_papers": sum(item.paper_count for item in deep_results),
        "cluster_themes": [item.theme for item in deep_results],
        "global_analyse": global_analyse,
        "cluster_summaries": cluster_summaries,
    }
