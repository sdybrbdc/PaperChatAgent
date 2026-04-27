from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


CapabilityKind = Literal["rag", "mcp", "skill", "agent"]


class ExecuteCapabilityRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False
