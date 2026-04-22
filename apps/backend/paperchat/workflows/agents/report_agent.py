from __future__ import annotations

from collections.abc import Sequence

from paperchat.providers import get_reasoning_chat_model
from paperchat.workflows.state import WritingSection

from .base import BaseWorkflowAgent


REPORT_SYSTEM_PROMPT = (
    "你是研究工作流中的报告智能体。"
    "请把章节草稿拼接成自然连贯的 Markdown 报告。"
    "保留客观、克制、研究型表达。"
)


class ReportAgent(BaseWorkflowAgent):
    def __init__(self) -> None:
        super().__init__(
            name="report_agent",
            system_prompt=REPORT_SYSTEM_PROMPT,
            model_factory=get_reasoning_chat_model,
        )

    async def build_report(self, *, topic: str, sections: Sequence[WritingSection]) -> str:
        section_text = "\n\n".join(f"## {section['title']}\n{section['content']}" for section in sections)
        prompt = (
            f"研究主题：{topic}\n\n"
            f"章节草稿：\n{section_text}\n\n"
            "请直接输出最终 Markdown 报告。"
        )
        generated = await self.ainvoke(prompt)
        if generated:
            return generated
        return self._fallback_report(topic=topic, sections=sections)

    def _fallback_report(self, *, topic: str, sections: Sequence[WritingSection]) -> str:
        rendered_sections = "\n\n".join(f"## {section['title']}\n{section['content']}" for section in sections)
        return (
            f"# {topic}\n\n"
            "本文档由 PaperChatAgent 研究工作流自动生成，当前输出用于主题探索和后续人工迭代。\n\n"
            f"{rendered_sections}".strip()
            + "\n"
        )
