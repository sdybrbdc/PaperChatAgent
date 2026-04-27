from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RagRetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    knowledge_base_ids: list[str] = Field(default_factory=list)
    conversation_id: str | None = None
    top_k: int = Field(default=8, ge=1, le=50)
    metadata_filter: dict[str, Any] = Field(default_factory=dict)


class RagSourcePayload(BaseModel):
    file_id: str
    knowledge_base_id: str
    title: str
    filename: str
    source_type: str
    source_uri: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagChunkPayload(BaseModel):
    id: str
    text: str
    score: float
    source: RagSourcePayload
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagRetrievePayload(BaseModel):
    query: str
    items: list[RagChunkPayload]
    total: int
    used_knowledge_base_ids: list[str]


class RagIndexFilePayload(BaseModel):
    file_id: str
    knowledge_base_id: str
    status: str
    chunk_count: int
    indexed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
