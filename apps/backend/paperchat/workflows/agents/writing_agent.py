from __future__ import annotations

from collections.abc import Sequence

from paperchat.workflows.state import DeepAnalysisResult, ReadingNote, SectionTask, WritingSection

from .sub_writing_agent import WritingDirectorAgent, run_parallel_writing


class WritingAgent:
    def __init__(self) -> None:
        self.writing_director = WritingDirectorAgent()

    async def run_full_writing(
        self,
        *,
        topic: str,
        reading_notes: Sequence[ReadingNote],
        deep_analysis_results: Sequence[DeepAnalysisResult],
        analysis_markdown: str,
        progress_callback=None,
    ) -> tuple[list[SectionTask], list[WritingSection]]:
        if progress_callback:
            await progress_callback("director", "正在生成写作大纲")
        outline = await self.writing_director.build_outline(
            topic=topic,
            analysis_markdown=analysis_markdown,
            deep_analysis_results=deep_analysis_results,
            progress_callback=progress_callback,
        )

        async def per_section_callback(order: int, phase: str, detail: str) -> None:
            if progress_callback:
                await progress_callback(f"section_{order}_{phase}", detail)

        sections = await run_parallel_writing(
            topic=topic,
            section_tasks=outline,
            reading_notes=list(reading_notes),
            deep_analysis_results=list(deep_analysis_results),
            analysis_markdown=analysis_markdown,
            per_section_callback=per_section_callback,
        )
        return outline, sections
