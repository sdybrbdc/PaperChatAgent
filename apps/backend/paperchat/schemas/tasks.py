from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TaskStatus = Literal["pending", "running", "completed", "failed", "canceled"]


class CreateTaskRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=2000)
    workflow_id: str = Field(default="smart_research_assistant")
    conversation_id: str | None = None
    max_papers: int = Field(default=6, ge=1, le=20)
    start_background: bool = True


class TaskListQuery(BaseModel):
    status: TaskStatus | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
