from __future__ import annotations

from enum import Enum, auto
from typing import Any, TypedDict

from pydantic import BaseModel


class WritingStage(Enum):
    INIT = auto()
    OUTLINE = auto()
    SECTION_SPLIT = auto()
    RETRIEVAL = auto()
    WRITING = auto()
    REVIEW = auto()
    COMPLETED = auto()


class SectionState(BaseModel):
    title: str
    content: str = ""
    completed: bool = False


class WritingState(TypedDict, total=False):
    user_request: str
    global_analysis: str
    sections: list[str]
    retrieved_docs: list[dict[str, Any]]
    writted_sections: list[SectionState]
    review_result: dict[str, Any]
    missing_tools: list[str]
