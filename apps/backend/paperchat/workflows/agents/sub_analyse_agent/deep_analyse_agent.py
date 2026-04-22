from __future__ import annotations

from collections.abc import Sequence
import json

from autogen_agentchat.agents import AssistantAgent

from paperchat.providers import get_autogen_reasoning_model_client
from paperchat.workflows.state import AnalysisCluster, DeepAnalysisResult, ReadingNote


DEEP_ANALYSE_AGENT_PROMPT = """
你是一位专业的学术研究分析师。

请围绕单个论文主题簇输出结构化 Markdown，覆盖：
## 技术发展趋势
## 方法对比
## 性能与适用性
## 局限与机会
"""


class DeepAnalyseAgent:
    def __init__(self) -> None:
        self.agent = AssistantAgent(
            name="deep_analyse_agent",
            description="负责对单个主题簇进行深度分析。",
            model_client=get_autogen_reasoning_model_client(),
            system_message=DEEP_ANALYSE_AGENT_PROMPT,
        )

    async def analyze_cluster(
        self,
        *,
        cluster: AnalysisCluster,
        reading_notes: Sequence[ReadingNote],
    ) -> DeepAnalysisResult:
        note_indexes = cluster.get("note_indexes", [])
        notes = [reading_notes[index] for index in note_indexes if index < len(reading_notes)]
        compact_notes = [
            {
                "title": note.get("title", ""),
                "published": note.get("published", ""),
                "core_problem": note.get("core_problem", ""),
                "matched_keywords": note.get("matched_keywords", []),
                "summary": (note.get("summary", "") or "")[:800],
            }
            for note in notes
        ]
        prompt = (
            f"聚类主题：{cluster.get('theme', '')}\n"
            f"关键词：{', '.join(cluster.get('keywords', []))}\n"
            f"论文数：{cluster.get('paper_count', 0)}\n"
            f"阅读卡片：\n{json.dumps(compact_notes, ensure_ascii=False, indent=2)}"
        )
        try:
            result = await self.agent.run(task=prompt)
            content = getattr(result.messages[-1], "content", "") if result.messages else ""
        except Exception:
            content = ""

        if not content:
            content = self._fallback_analysis(cluster=cluster, notes=notes)

        return {
            "cluster_id": cluster.get("cluster_id", 0),
            "theme": cluster.get("theme", ""),
            "keywords": list(cluster.get("keywords", [])),
            "paper_count": cluster.get("paper_count", len(notes)),
            "representative_titles": list(cluster.get("representative_titles", [])),
            "analysis_markdown": content,
        }

    def _fallback_analysis(self, *, cluster: AnalysisCluster, notes: Sequence[ReadingNote]) -> str:
        timeline = []
        for note in notes:
            year = (note.get("published") or "")[:4]
            title = note.get("title", "")
            if year:
                timeline.append(f"- {year}：{title}")

        methods = []
        for note in notes[:4]:
            methods.append(
                f"- {note.get('title', '未命名论文')}：{note.get('core_problem', '') or note.get('summary', '')[:120]}"
            )

        return (
            "## 技术发展趋势\n"
            f"- 当前主题集中在“{cluster.get('theme', '未命名主题')}”附近展开。\n"
            f"{chr(10).join(timeline) or '- 当前样本不足以形成清晰时间线'}\n\n"
            "## 方法对比\n"
            f"{chr(10).join(methods) or '- 当前样本不足以形成方法对比'}\n\n"
            "## 性能与适用性\n"
            "- 现有阅读卡片更多反映任务设定和方法线索，定量结果仍需后续补充原文或表格级证据。\n"
            "- 可以优先把共同指标、数据集和场景边界单独拉出来做对比表。\n\n"
            "## 局限与机会\n"
            "- 当前样本规模仍偏小，尚不足以替代系统综述。\n"
            "- 下一步适合沿代表论文扩引、补数据集与指标，再形成更完整的谱系分析。"
        )
