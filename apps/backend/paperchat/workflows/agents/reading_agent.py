from __future__ import annotations

from collections.abc import Sequence

from paperchat.workflows.state import ReadingNote, ResearchPaper


def _first_sentence(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    for marker in [". ", "。", "! ", "? ", "\n"]:
        if marker in cleaned:
            return cleaned.split(marker, 1)[0].strip()
    return cleaned[:180].strip()


class ReadingAgent:
    def extract_notes(
        self,
        *,
        topic: str,
        keywords: Sequence[str],
        papers: Sequence[ResearchPaper],
    ) -> list[ReadingNote]:
        notes: list[ReadingNote] = []
        keyword_list = [keyword.strip() for keyword in keywords if keyword.strip()]

        for paper in papers:
            title = paper.get("title", "").strip()
            summary = " ".join((paper.get("summary") or "").split())
            searchable = f"{title} {summary}".lower()
            matched_keywords = [keyword for keyword in keyword_list if keyword.lower() in searchable]
            year = (paper.get("published") or "")[:4]
            relevance_prefix = f"与主题“{topic}”直接相关"
            if matched_keywords:
                relevance_prefix += f"，命中关键词：{', '.join(matched_keywords[:3])}"
            elif year:
                relevance_prefix += f"，可作为 {year} 年相关研究样本"

            notes.append(
                {
                    "paper_id": paper.get("entry_id") or title,
                    "title": title,
                    "published": paper.get("published", ""),
                    "authors": list(paper.get("authors", [])),
                    "matched_keywords": matched_keywords,
                    "core_problem": _first_sentence(summary) or title,
                    "summary": summary,
                    "relevance": relevance_prefix,
                }
            )
        return notes
