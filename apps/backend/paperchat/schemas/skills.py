from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SkillSourceType = Literal["local", "repo", "builtin", "custom"]
SkillStatus = Literal["enabled", "disabled"]


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    source_type: SkillSourceType = "custom"
    source_uri: str = ""
    entrypoint: str = ""
    status: SkillStatus = "disabled"
    content: str | None = None
    manifest: dict[str, Any] = Field(default_factory=dict)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    source_type: SkillSourceType | None = None
    source_uri: str | None = None
    entrypoint: str | None = None
    status: SkillStatus | None = None
    content: str | None = None
    manifest: dict[str, Any] | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class SkillImportRequest(BaseModel):
    source_uri: str = ""
    status: SkillStatus = "disabled"


class SkillTestRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


class SkillFileUpdateRequest(BaseModel):
    path: str = Field(min_length=1)
    content: str = ""


class SkillFileAddRequest(BaseModel):
    path: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=255)
    content: str = ""


class SkillFileDeleteRequest(BaseModel):
    path: str = Field(min_length=1)


class SkillPayload(BaseModel):
    id: str
    name: str
    description: str
    source_type: str
    source_uri: str
    entrypoint: str
    status: str
    manifest: dict[str, Any]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    metadata: dict[str, Any]
    folder: dict[str, Any] | None = None
    content: str = ""
    content_preview: str = ""
    content_source: str = ""
    file_count: int = 0
    as_tool_name: str = ""
    trigger_phrases: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class SkillListPayload(BaseModel):
    items: list[SkillPayload]


class SkillTestPayload(BaseModel):
    ok: bool
    executed: bool
    message: str
    output: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
