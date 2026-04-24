from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.cluster import KMeans

from paperchat.agents.research_orchestrator.runtime_support import (
    call_autogen_agent,
    compact_json,
    extract_json_object,
)
from paperchat.agents.research_orchestrator.state_models import ExtractedPaperData, ExtractedPapersData
from paperchat.prompts.research_orchestrator import CLUSTERING_AGENT_PROMPT
from paperchat.providers import get_embedding_client


@dataclass
class PaperCluster:
    cluster_id: int
    papers: list[dict[str, Any]]
    theme_description: str
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "theme": self.theme_description,
            "keywords": self.keywords,
            "paper_count": len(self.papers),
            "papers": self.papers,
        }


def _paper_text(paper: ExtractedPaperData) -> str:
    methodology = paper.key_methodology
    return " ".join(
        [
            paper.title,
            paper.core_problem,
            methodology.name,
            methodology.principle,
            paper.main_results,
            " ".join(paper.contributions),
        ]
    ).strip()


async def _embed_texts(texts: list[str]) -> np.ndarray:
    client = get_embedding_client()
    embeddings = await asyncio.to_thread(client.embed_documents, texts)
    return np.array(embeddings)


def _cluster_by_embeddings(papers: list[ExtractedPaperData], embeddings: np.ndarray) -> list[list[ExtractedPaperData]]:
    if len(papers) <= 2:
        return [papers]
    n_clusters = min(3, max(1, len(papers) // 2), len(papers))
    if n_clusters <= 1:
        return [papers]
    labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(embeddings)
    groups: list[list[ExtractedPaperData]] = [[] for _ in range(n_clusters)]
    for paper, label in zip(papers, labels, strict=False):
        groups[int(label)].append(paper)
    return [group for group in groups if group]


def _fallback_groups(papers: list[ExtractedPaperData]) -> list[list[ExtractedPaperData]]:
    if len(papers) <= 4:
        return [papers]
    midpoint = max(1, len(papers) // 2)
    return [papers[:midpoint], papers[midpoint:]]


async def _name_cluster(
    cluster_id: int,
    papers: list[ExtractedPaperData],
    *,
    model_slot: str,
) -> PaperCluster:
    paper_dicts = [paper.model_dump() for paper in papers]
    try:
        response = await call_autogen_agent(
            name="paper_cluster_agent",
            system_prompt=CLUSTERING_AGENT_PROMPT,
            user_prompt=f"请为这个论文簇生成主题名和关键词：\n{compact_json(paper_dicts, limit=5000)}",
            model_slot=model_slot,
            reasoning=True,
        )
        data = extract_json_object(response)
        theme = str(data.get("theme") or data.get("主题") or "未分类研究主题")
        keywords = data.get("keywords") or data.get("关键词") or []
        if isinstance(keywords, str):
            keywords = [item.strip() for item in keywords.replace("，", ",").split(",") if item.strip()]
    except Exception:
        theme = papers[0].key_methodology.name or papers[0].title or "未分类研究主题"
        keywords = [word for word in [papers[0].key_methodology.name, "research"] if word]
    return PaperCluster(cluster_id=cluster_id, papers=paper_dicts, theme_description=theme, keywords=keywords[:5])


async def run_cluster_analysis(
    extracted_data: ExtractedPapersData,
    *,
    model_slot: str = "reasoning_model",
) -> list[PaperCluster]:
    papers = extracted_data.papers
    if not papers:
        return []
    try:
        embeddings = await _embed_texts([_paper_text(paper) for paper in papers])
        groups = _cluster_by_embeddings(papers, embeddings)
    except Exception:
        groups = _fallback_groups(papers)
    return await asyncio.gather(
        *[_name_cluster(index, group, model_slot=model_slot) for index, group in enumerate(groups)]
    )
