from __future__ import annotations

from typing import TypedDict

from paperchat.workflows.state import DeepAnalysisResult, ReadingNote, RetrievedContext, ReviewResult, SectionTask, WritingSection


class SectionWritingContext(TypedDict):
    topic: str
    section_task: SectionTask
    reading_notes: list[ReadingNote]
    deep_analysis_results: list[DeepAnalysisResult]
    analysis_markdown: str


class SectionWritingResult(TypedDict):
    section: WritingSection
    review: ReviewResult
    contexts: list[RetrievedContext]
