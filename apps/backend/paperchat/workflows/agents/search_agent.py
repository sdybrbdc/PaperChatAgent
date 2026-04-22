from __future__ import annotations

from collections.abc import Sequence
import re

from paperchat.providers import get_reasoning_chat_model

from .base import BaseWorkflowAgent


SEARCH_SYSTEM_PROMPT = (
    "你是研究工作流中的搜索规划智能体。"
    "请把用户主题收束成适合论文检索的短查询。"
    "只输出 3 到 4 行查询文本，每行一个，不要解释。"
)


class SearchPlanningAgent(BaseWorkflowAgent):
    def __init__(self) -> None:
        super().__init__(
            name="search_agent",
            system_prompt=SEARCH_SYSTEM_PROMPT,
            model_factory=get_reasoning_chat_model,
        )

    async def plan_queries(self, *, topic: str, keywords: Sequence[str]) -> list[str]:
        prompt = (
            f"研究主题：{topic}\n"
            f"关键词：{', '.join(keyword for keyword in keywords if keyword).strip() or '无'}\n\n"
            "请输出适合 arXiv / 学术搜索的英文或中英混合查询。"
        )
        generated = await self.ainvoke(prompt)
        if generated:
            queries = self._parse_queries(generated)
            if queries:
                return queries[:4]
        return self._fallback_queries(topic=topic, keywords=keywords)

    def _parse_queries(self, raw_text: str) -> list[str]:
        queries: list[str] = []
        for line in raw_text.splitlines():
            cleaned = re.sub(r"^\s*(?:[-*]|\d+[.)]|query\s*\d+\s*:)\s*", "", line, flags=re.I).strip()
            cleaned = cleaned.strip("`\"' ")
            if cleaned:
                queries.append(cleaned)
        return self._dedupe(queries)

    def _fallback_queries(self, *, topic: str, keywords: Sequence[str]) -> list[str]:
        candidates = [topic.strip()]
        keyword_text = " ".join(keyword.strip() for keyword in keywords if keyword.strip())
        if keyword_text:
            candidates.append(keyword_text)
            candidates.append(f"{keyword_text} survey")
        if topic.strip():
            candidates.append(f"{topic.strip()} survey")
        return self._dedupe(candidates)[:4]

    def _dedupe(self, items: Sequence[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            normalized = " ".join(item.split())
            key = normalized.lower()
            if not normalized or key in seen:
                continue
            seen.add(key)
            result.append(normalized)
        return result
