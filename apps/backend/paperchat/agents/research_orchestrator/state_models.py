from __future__ import annotations

from enum import Enum
from typing import Any, TypedDict

from pydantic import BaseModel, Field


class ExecutionState(str, Enum):
    INITIALIZING = "initializing"
    SEARCHING = "searching"
    READING = "reading"
    ANALYZING = "analyzing"
    WRITING_DIRECTOR = "writing_director"
    SECTION_WRITING = "section_writing"
    WRITING = "writing"
    RETRIEVING = "retrieving"
    REVIEWING = "reviewing"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


class BackToFrontData(BaseModel):
    step: str
    state: str
    data: Any = None


class KeyMethodology(BaseModel):
    name: str = ""
    principle: str = ""
    novelty: str = ""


class ExtractedPaperData(BaseModel):
    paper_id: str = ""
    title: str = ""
    core_problem: str = ""
    key_methodology: KeyMethodology = Field(default_factory=KeyMethodology)
    datasets_used: list[str] = Field(default_factory=list)
    evaluation_metrics: list[str] = Field(default_factory=list)
    main_results: str = ""
    limitations: str = ""
    contributions: list[str] = Field(default_factory=list)
    source_url: str = ""


class ExtractedPapersData(BaseModel):
    papers: list[ExtractedPaperData] = Field(default_factory=list)


class NodeError(BaseModel):
    search_node_error: str | None = None
    reading_node_error: str | None = None
    analyse_node_error: str | None = None
    writing_node_error: str | None = None
    report_node_error: str | None = None
    error: str | None = None

    def has_error(self) -> bool:
        return any(
            [
                self.search_node_error,
                self.reading_node_error,
                self.analyse_node_error,
                self.writing_node_error,
                self.report_node_error,
                self.error,
            ]
        )

    def message(self) -> str:
        return next(
            (
                item
                for item in [
                    self.search_node_error,
                    self.reading_node_error,
                    self.analyse_node_error,
                    self.writing_node_error,
                    self.report_node_error,
                    self.error,
                ]
                if item
            ),
            "",
        )


class PaperAgentState(BaseModel):
    user_request: str
    max_papers: int = 6
    current_step: ExecutionState = ExecutionState.INITIALIZING
    error: NodeError = Field(default_factory=NodeError)
    search_queries: list[str] = Field(default_factory=list)
    search_results: list[dict[str, Any]] = Field(default_factory=list)
    extracted_data: ExtractedPapersData = Field(default_factory=ExtractedPapersData)
    cluster_analysis: list[dict[str, Any]] = Field(default_factory=list)
    deep_analysis: list[dict[str, Any]] = Field(default_factory=list)
    global_analysis: dict[str, Any] = Field(default_factory=dict)
    analyse_results: dict[str, Any] = Field(default_factory=dict)
    outline: list[str] = Field(default_factory=list)
    retrieval_results: dict[str, Any] = Field(default_factory=dict)
    review_result: dict[str, Any] = Field(default_factory=dict)
    writted_sections: list[str] = Field(default_factory=list)
    report_markdown: str = ""
    report_summary: str = ""
    missing_tools: list[str] = Field(default_factory=list)
    skipped_capabilities: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class State(TypedDict):
    run_id: str
    value: PaperAgentState


class ConfigSchema(TypedDict, total=False):
    run_id: str
