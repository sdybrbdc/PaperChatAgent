from __future__ import annotations

import asyncio

from autogen_agentchat.base import TaskResult

from paperchat.workflows.state import DeepAnalysisResult, ReadingNote, ReviewResult, SectionTask, WritingSection

from .review_agent import parse_review_result
from .writing_chat_group import create_writing_group


def _normalize_review(text: str) -> ReviewResult:
    if not text.strip():
        return {"approved": False, "feedback": "未收到审查结果"}
    return parse_review_result(text)


async def run_parallel_writing(
    *,
    topic: str,
    section_tasks: list[SectionTask],
    reading_notes: list[ReadingNote],
    deep_analysis_results: list[DeepAnalysisResult],
    analysis_markdown: str,
    per_section_callback=None,
) -> list[WritingSection]:
    async def write_single_section(section_task: SectionTask) -> WritingSection:
        order = section_task.get("order", 0)
        task_prompt = f"""请根据以下内容完成当前章节：
研究主题：{topic}
当前章节：{section_task.get('title', '')}
章节说明：{section_task.get('description', '')}

请围绕该章节完成写作与审查协作。
"""

        team, runtime_state = create_writing_group(
            reading_notes=reading_notes,
            deep_analysis_results=deep_analysis_results,
            analysis_markdown=analysis_markdown,
        )

        latest_writing_content = ""
        latest_review_text = ""

        async for chunk in team.run_stream(task=task_prompt):
            if isinstance(chunk, TaskResult):
                continue

            chunk_type = getattr(chunk, "type", "")
            source = getattr(chunk, "source", "")

            if chunk_type == "ModelClientStreamingChunkEvent" and source == "writing_agent":
                if per_section_callback:
                    await per_section_callback(order, "writing_stream", getattr(chunk, "content", ""))
                continue

            if chunk_type == "ToolCallSummaryMessage" and source == "retrieval_agent":
                if per_section_callback:
                    await per_section_callback(order, "retrieval", "retrieval_agent 已返回检索摘要")
                continue

            if chunk_type == "TextMessage":
                content = getattr(chunk, "content", "") or ""
                if source == "writing_agent":
                    latest_writing_content = content
                    if per_section_callback:
                        await per_section_callback(order, "writing", content)
                elif source == "review_agent":
                    latest_review_text = content
                    if per_section_callback:
                        await per_section_callback(order, "review", content)
                elif source == "retrieval_agent":
                    if per_section_callback:
                        await per_section_callback(order, "retrieval", content)

        review_result = _normalize_review(latest_review_text)
        return {
            "order": order,
            "title": section_task.get("title", ""),
            "description": section_task.get("description", ""),
            "content": latest_writing_content,
            "retrieved_contexts": list(runtime_state.get("retrieved_contexts", [])),
            "review_feedback": review_result.get("feedback", ""),
            "approved": bool(review_result.get("approved", False)),
        }

    results = await asyncio.gather(*[write_single_section(task) for task in section_tasks])
    return sorted(results, key=lambda item: item.get("order", 0))
