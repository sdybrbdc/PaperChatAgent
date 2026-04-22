from __future__ import annotations

from collections.abc import Sequence
import re

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult

from paperchat.providers import get_autogen_reasoning_model_client
from paperchat.workflows.state import DeepAnalysisResult, SectionTask


WRITING_DIRECTOR_AGENT_PROMPT = """
你是一位专业的写作主管，负责把研究报告拆分成结构清晰的小节任务。

输出要求：
1. 生成 3 到 6 个小节。
2. 每行一个小节。
3. 格式固定为：1. 标题 (写作说明)
4. 不要输出额外解释。
"""


class WritingDirectorAgent:
    def __init__(self) -> None:
        self.agent = AssistantAgent(
            name="writing_director_agent",
            description="负责拆分写作任务并生成章节大纲。",
            model_client=get_autogen_reasoning_model_client(),
            system_message=WRITING_DIRECTOR_AGENT_PROMPT,
            model_client_stream=True,
        )

    async def build_outline(
        self,
        *,
        topic: str,
        analysis_markdown: str,
        deep_analysis_results: Sequence[DeepAnalysisResult],
        progress_callback=None,
    ) -> list[SectionTask]:
        themes = [item.get("theme", "") for item in deep_analysis_results if item.get("theme")]
        prompt = (
            f"研究主题：{topic}\n"
            f"主题簇：{themes}\n\n"
            f"全局分析：\n{analysis_markdown}\n\n"
            "请为这份研究报告生成章节清单。"
        )
        outline_text = ""
        async for chunk in self.agent.run_stream(task=prompt):
            if isinstance(chunk, TaskResult):
                continue
            chunk_type = getattr(chunk, "type", "")
            if chunk_type == "ModelClientStreamingChunkEvent":
                if progress_callback:
                    await progress_callback("director_stream", getattr(chunk, "content", ""))
                continue
            if chunk_type == "TextMessage":
                outline_text = getattr(chunk, "content", "") or ""

        parsed = self._parse_outline(outline_text)
        if parsed:
            return parsed
        return self._fallback_outline(topic=topic, themes=themes)

    def _parse_outline(self, text: str) -> list[SectionTask]:
        tasks: list[SectionTask] = []
        for line in text.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            cleaned = re.sub(r"^\d+(?:\.\d+)?[.)]?\s*", "", cleaned)
            title, description = cleaned, ""
            if "(" in cleaned and ")" in cleaned:
                title = cleaned.split("(", 1)[0].strip()
                description = cleaned.rsplit("(", 1)[-1].rstrip(")").strip()
            if title:
                tasks.append(
                    {
                        "order": len(tasks) + 1,
                        "title": title,
                        "description": description or f"围绕 {title} 展开系统性说明。",
                    }
                )
        return tasks

    def _fallback_outline(self, *, topic: str, themes: Sequence[str]) -> list[SectionTask]:
        theme_hint = "、".join(theme for theme in themes[:3] if theme) or topic
        return [
            {"order": 1, "title": "研究背景与问题定义", "description": f"界定 {topic} 的任务边界、研究动机与核心问题。"},
            {"order": 2, "title": "主题谱系与代表工作", "description": f"围绕 {theme_hint} 梳理代表论文与主要技术分支。"},
            {"order": 3, "title": "方法与应用分析", "description": "对比不同技术路线、应用场景和适用边界。"},
            {"order": 4, "title": "局限与后续方向", "description": "总结当前方案局限，并提出下一步研究建议。"},
        ]
