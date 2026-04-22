from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
import json
import re

from autogen_agentchat.agents import AssistantAgent
from autogen_core.tools import FunctionTool

from paperchat.providers import get_autogen_tool_call_model_client
from paperchat.workflows.state import DeepAnalysisResult, ReadingNote, RetrievedContext


RETRIEVAL_AGENT_PROMPT = """
你是一个检索助手，负责为当前章节补充资料。

工作规则：
1. 先根据当前章节任务生成 2 到 4 个检索 query。
2. 必须调用 `retrieval_tool` 获取上下文。
3. 不要写正文，只输出检索得到的关键证据。
4. 如果资料不足，要明确指出资料缺口。
"""

TOKEN_RE = re.compile(r"[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9_-]{1,}")


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


class RetrievalAgent:
    def retrieve(
        self,
        *,
        querys: Sequence[str],
        reading_notes: Sequence[ReadingNote],
        deep_analysis_results: Sequence[DeepAnalysisResult],
        analysis_markdown: str,
        top_k: int = 4,
    ) -> list[RetrievedContext]:
        query_tokens = Counter(_tokenize(" ".join(querys)))
        contexts: list[RetrievedContext] = []

        for note in reading_notes:
            source_text = " ".join(
                [
                    note.get("title", ""),
                    note.get("core_problem", ""),
                    note.get("summary", ""),
                    " ".join(note.get("matched_keywords", [])),
                ]
            )
            score = self._score(query_tokens, source_text)
            if score <= 0:
                continue
            contexts.append(
                {
                    "source_type": "reading_note",
                    "source_title": note.get("title", "阅读卡片"),
                    "excerpt": (note.get("summary") or note.get("core_problem") or "")[:480],
                    "score": round(score, 4),
                }
            )

        for result in deep_analysis_results:
            source_text = " ".join(
                [
                    result.get("theme", ""),
                    " ".join(result.get("keywords", [])),
                    result.get("analysis_markdown", ""),
                ]
            )
            score = self._score(query_tokens, source_text)
            if score <= 0:
                continue
            contexts.append(
                {
                    "source_type": "deep_analysis",
                    "source_title": result.get("theme", "主题分析"),
                    "excerpt": result.get("analysis_markdown", "")[:600],
                    "score": round(score, 4),
                }
            )

        summary_score = self._score(query_tokens, analysis_markdown)
        if summary_score > 0:
            contexts.append(
                {
                    "source_type": "global_analysis",
                    "source_title": "全局分析",
                    "excerpt": analysis_markdown[:800],
                    "score": round(summary_score, 4),
                }
            )

        contexts.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return contexts[:top_k]

    def format_contexts(self, contexts: Sequence[RetrievedContext]) -> str:
        if not contexts:
            return "未检索到直接相关的上下文。"
        rendered = []
        for index, context in enumerate(contexts, start=1):
            rendered.append(
                f"[{index}] 来源类型：{context.get('source_type', '')}\n"
                f"标题：{context.get('source_title', '')}\n"
                f"摘录：{context.get('excerpt', '')}\n"
                f"相关度：{context.get('score', 0.0)}"
            )
        return "\n\n".join(rendered)

    def _score(self, query_tokens: Counter[str], source_text: str) -> float:
        source_tokens = Counter(_tokenize(source_text))
        if not source_tokens:
            return 0.0
        overlap = sum(min(count, source_tokens.get(token, 0)) for token, count in query_tokens.items())
        return overlap / max(4, sum(query_tokens.values()))


def create_retrieval_agent(
    *,
    reading_notes: Sequence[ReadingNote],
    deep_analysis_results: Sequence[DeepAnalysisResult],
    analysis_markdown: str,
    runtime_state: dict,
) -> AssistantAgent:
    engine = RetrievalAgent()

    async def retrieval_tool(querys: list[str]) -> str:
        contexts = engine.retrieve(
            querys=querys,
            reading_notes=reading_notes,
            deep_analysis_results=deep_analysis_results,
            analysis_markdown=analysis_markdown,
        )
        runtime_state["retrieved_contexts"] = contexts
        return engine.format_contexts(contexts)

    retriever = FunctionTool(
        retrieval_tool,
        name="retrieval_tool",
        description="根据 query 列表检索与当前章节相关的阅读卡片和主题分析上下文。",
    )

    return AssistantAgent(
        name="retrieval_agent",
        description="负责检索当前章节所需的补充资料。",
        model_client=get_autogen_tool_call_model_client(),
        system_message=RETRIEVAL_AGENT_PROMPT,
        tools=[retriever],
        reflect_on_tool_use=False,
        tool_call_summary_format="{result}",
    )
