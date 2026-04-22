from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
import math
import re

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult

from paperchat.providers import get_autogen_reasoning_model_client, get_embedding_client
from paperchat.workflows.state import AnalysisCluster, ReadingNote


CLUSTER_AGENT_PROMPT = """
你是论文主题聚类助手。

请基于一组论文阅读卡片，输出：
主题：<一句中文主题概括>
关键词：<3到5个关键词，用中文逗号分隔>
"""

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "using",
    "based",
    "from",
    "into",
    "toward",
    "towards",
    "study",
    "research",
    "system",
    "paper",
    "approach",
    "method",
    "analysis",
    "agent",
    "agents",
    "review",
}


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _mean_vector(vectors: Sequence[Sequence[float]]) -> list[float]:
    if not vectors:
        return []
    length = len(vectors[0])
    return [sum(vector[index] for vector in vectors) / len(vectors) for index in range(length)]


class PaperClusterAgent:
    def __init__(self) -> None:
        self.naming_agent = AssistantAgent(
            name="cluster_agent",
            description="负责为论文簇生成主题和关键词。",
            model_client=get_autogen_reasoning_model_client(),
            system_message=CLUSTER_AGENT_PROMPT,
            model_client_stream=True,
        )

    async def cluster_notes(self, notes: Sequence[ReadingNote]) -> list[AnalysisCluster]:
        if not notes:
            return []

        embeddings = self._embed_notes(notes)
        groups = self._group_embeddings(embeddings)
        clusters: list[AnalysisCluster] = []

        for cluster_id, indexes in enumerate(groups, start=1):
            grouped_notes = [notes[index] for index in indexes]
            theme, keywords = await self._name_cluster(grouped_notes)
            clusters.append(
                {
                    "cluster_id": cluster_id,
                    "theme": theme,
                    "keywords": keywords,
                    "paper_count": len(grouped_notes),
                    "note_indexes": indexes,
                    "representative_titles": [note.get("title", "") for note in grouped_notes[:3] if note.get("title")],
                }
            )
        return clusters

    async def _name_cluster(self, notes: Sequence[ReadingNote]) -> tuple[str, list[str]]:
        compact = []
        for note in notes[:4]:
            compact.append(
                {
                    "title": note.get("title", ""),
                    "core_problem": note.get("core_problem", ""),
                    "matched_keywords": note.get("matched_keywords", []),
                }
            )
        result = await self.naming_agent.run(task=f"聚类样本：{compact}")
        if isinstance(result, TaskResult) and result.messages:
            content = getattr(result.messages[-1], "content", "") or ""
            theme, keywords = self._parse_response(content)
            if theme and keywords:
                return theme, keywords
        return self._fallback_name(notes)

    def _parse_response(self, text: str) -> tuple[str, list[str]]:
        theme = ""
        keywords: list[str] = []
        for line in text.splitlines():
            cleaned = line.strip()
            if cleaned.startswith("主题"):
                theme = cleaned.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif cleaned.startswith("关键词"):
                keyword_text = cleaned.split("：", 1)[-1].split(":", 1)[-1].strip()
                for splitter in ("，", ",", "；", ";", " "):
                    if splitter in keyword_text:
                        keywords = [item.strip() for item in keyword_text.split(splitter) if item.strip()]
                        break
                if not keywords and keyword_text:
                    keywords = [keyword_text]
        return theme, keywords[:5]

    def _fallback_name(self, notes: Sequence[ReadingNote]) -> tuple[str, list[str]]:
        token_counter = Counter()
        matched_counter = Counter()
        for note in notes:
            matched_counter.update(keyword for keyword in note.get("matched_keywords", []) if keyword)
            title = note.get("title", "")
            for token in re.findall(r"[A-Za-z][A-Za-z-]{2,}", title.lower()):
                if token not in STOPWORDS:
                    token_counter[token] += 1

        keywords = [keyword for keyword, _ in matched_counter.most_common(5)]
        if not keywords:
            keywords = [token for token, _ in token_counter.most_common(5)]
        if not keywords:
            keywords = ["research"]
        theme = " / ".join(keywords[:2]).strip(" /") or "研究主题聚类"
        return theme, keywords[:5]

    def _embed_notes(self, notes: Sequence[ReadingNote]) -> list[list[float]]:
        texts = []
        for note in notes:
            texts.append(
                " ".join(
                    part
                    for part in [
                        note.get("title", ""),
                        note.get("core_problem", ""),
                        note.get("summary", ""),
                        " ".join(note.get("matched_keywords", [])),
                    ]
                    if part
                )
            )

        try:
            embedder = get_embedding_client()
            return [list(item) for item in embedder.embed_documents(texts)]
        except Exception:
            return [[float(len(text)), float(index + 1)] for index, text in enumerate(texts)]

    def _group_embeddings(self, embeddings: Sequence[Sequence[float]]) -> list[list[int]]:
        if len(embeddings) <= 2:
            return [list(range(len(embeddings)))]

        max_clusters = max(1, min(4, round(math.sqrt(len(embeddings)))))
        threshold = 0.84 if len(embeddings) <= 6 else 0.8
        groups: list[list[int]] = []
        centroids: list[list[float]] = []

        for index, embedding in enumerate(embeddings):
            if not centroids:
                groups.append([index])
                centroids.append(list(embedding))
                continue

            similarities = [_cosine_similarity(embedding, centroid) for centroid in centroids]
            best_similarity = max(similarities)
            best_index = similarities.index(best_similarity)

            if best_similarity >= threshold or len(groups) >= max_clusters:
                groups[best_index].append(index)
                centroid_vectors = [embeddings[item_index] for item_index in groups[best_index]]
                centroids[best_index] = _mean_vector(centroid_vectors)
            else:
                groups.append([index])
                centroids.append(list(embedding))

        return groups
