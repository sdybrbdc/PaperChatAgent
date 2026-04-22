from __future__ import annotations

from typing import Any, TypedDict


class ResearchPaper(TypedDict, total=False):
    title: str
    summary: str
    entry_id: str
    published: str
    authors: list[str]
    pdf_url: str | None
    query: str


class ReadingNote(TypedDict, total=False):
    paper_id: str
    title: str
    published: str
    authors: list[str]
    matched_keywords: list[str]
    core_problem: str
    summary: str
    relevance: str


class AnalysisCluster(TypedDict, total=False):
    cluster_id: int
    theme: str
    keywords: list[str]
    paper_count: int
    note_indexes: list[int]
    representative_titles: list[str]


class DeepAnalysisResult(TypedDict, total=False):
    cluster_id: int
    theme: str
    keywords: list[str]
    paper_count: int
    representative_titles: list[str]
    analysis_markdown: str


class SectionTask(TypedDict, total=False):
    order: int
    title: str
    description: str


class RetrievedContext(TypedDict, total=False):
    source_type: str
    source_title: str
    excerpt: str
    score: float


class ReviewResult(TypedDict, total=False):
    approved: bool
    feedback: str


class WritingSection(TypedDict, total=False):
    order: int
    title: str
    description: str
    content: str
    retrieved_contexts: list[RetrievedContext]
    review_feedback: str
    approved: bool


class ResearchWorkflowState(TypedDict):
    task_id: str
    user_id: str
    workspace_id: str
    topic: str
    keywords: list[str]
    source_config: dict[str, Any]
    search_queries: list[str]
    papers: list[ResearchPaper]
    reading_notes: list[ReadingNote]
    analysis_clusters: list[AnalysisCluster]
    deep_analysis_results: list[DeepAnalysisResult]
    analysis_markdown: str
    writing_outline: list[SectionTask]
    writing_sections: list[WritingSection]
    report_markdown: str
    report_summary: str
    last_detail: str
    failed_node: str | None
    error: str | None


class WorkflowNodeExecutionError(RuntimeError):
    def __init__(self, *, node_id: str, message: str):
        super().__init__(message)
        self.node_id = node_id
        self.message = message
