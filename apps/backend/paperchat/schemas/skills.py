from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SkillSourceType = Literal["local", "repo", "builtin"]
SkillStatus = Literal["enabled", "disabled"]


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    source_type: SkillSourceType = "local"
    source_uri: str = ""
    entrypoint: str = ""
    status: SkillStatus = "disabled"
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
    manifest: dict[str, Any] | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class SkillImportRequest(BaseModel):
    source_uri: str = Field(min_length=1)
    status: SkillStatus = "disabled"


class SkillTestRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


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
