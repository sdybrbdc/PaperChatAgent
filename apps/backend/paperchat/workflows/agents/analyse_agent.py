from __future__ import annotations

import asyncio
from collections.abc import Sequence

from paperchat.workflows.state import AnalysisCluster, DeepAnalysisResult, ReadingNote

from .sub_analyse_agent import DeepAnalyseAgent, GlobalAnalyseAgent, PaperClusterAgent


class AnalysisAgent:
    def __init__(self) -> None:
        self.cluster_agent = PaperClusterAgent()
        self.deep_agent = DeepAnalyseAgent()
        self.global_agent = GlobalAnalyseAgent()

    async def run_full_analysis(
        self,
        *,
        topic: str,
        keywords: Sequence[str],
        reading_notes: Sequence[ReadingNote],
        progress_callback=None,
    ) -> tuple[str, list[AnalysisCluster], list[DeepAnalysisResult]]:
        if progress_callback:
            await progress_callback("cluster", "正在聚类阅读卡片")
        clusters = await self.cluster_agent.cluster_notes(reading_notes)

        if progress_callback:
            await progress_callback("deep_analysis", f"已形成 {len(clusters)} 个主题簇，开始并行深度分析")
        deep_results = await asyncio.gather(
            *[
                self.deep_agent.analyze_cluster(cluster=cluster, reading_notes=reading_notes)
                for cluster in clusters
            ]
        )

        if progress_callback:
            await progress_callback("global_analysis", "正在汇总多主题分析结果")
        analysis_markdown = await self.global_agent.build_global_analysis(
            topic=topic,
            deep_results=deep_results,
            progress_callback=progress_callback,
        )
        return analysis_markdown, clusters, deep_results
