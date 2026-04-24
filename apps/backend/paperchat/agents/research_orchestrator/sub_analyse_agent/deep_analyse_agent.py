from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from paperchat.agents.research_orchestrator.runtime_support import call_autogen_agent, compact_json
from paperchat.agents.research_orchestrator.sub_analyse_agent.cluster_agent import PaperCluster
from paperchat.prompts.research_orchestrator import DEEP_ANALYSE_AGENT_PROMPT


@dataclass
class DeepAnalyseResult:
    cluster_id: int
    theme: str
    keywords: list[str]
    paper_count: int
    deep_analyse: str
    papers: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "theme": self.theme,
            "keywords": self.keywords,
            "paper_count": self.paper_count,
            "deep_analyse": self.deep_analyse,
            "papers": self.papers,
        }


async def run_deep_analysis(cluster: PaperCluster, *, model_slot: str = "reasoning_model") -> DeepAnalyseResult:
    prompt = f"""
聚类主题：{cluster.theme_description}
关键词：{", ".join(cluster.keywords)}
论文数据：
{compact_json(cluster.papers, limit=9000)}

请输出该主题簇的深度分析。
"""
    try:
        analysis = await call_autogen_agent(
            name="deep_analyse_agent",
            system_prompt=DEEP_ANALYSE_AGENT_PROMPT,
            user_prompt=prompt,
            model_slot=model_slot,
            reasoning=True,
        )
    except Exception as exc:
        analysis = f"深度分析失败：{exc}"
    return DeepAnalyseResult(
        cluster_id=cluster.cluster_id,
        theme=cluster.theme_description,
        keywords=cluster.keywords,
        paper_count=len(cluster.papers),
        deep_analyse=analysis,
        papers=cluster.papers,
    )
