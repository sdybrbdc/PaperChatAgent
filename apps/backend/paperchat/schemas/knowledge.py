from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


KnowledgeVisibility = Literal["private", "shared"]
KnowledgeStatus = Literal["active", "archived"]
KnowledgeFileStatus = Literal["pending", "indexed", "failed"]


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    visibility: KnowledgeVisibility = "private"
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    visibility: KnowledgeVisibility | None = None
    status: KnowledgeStatus | None = None
    metadata: dict[str, Any] | None = None


class KnowledgeBasePayload(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    visibility: KnowledgeVisibility
    status: KnowledgeStatus
    metadata: dict[str, Any] = Field(default_factory=dict)
    file_count: int = 0
    indexed_file_count: int = 0
    created_at: datetime
    updated_at: datetime


class KnowledgeFilePayload(BaseModel):
    id: str
    knowledge_base_id: str
    user_id: str
    filename: str
    source_type: str
    source_uri: str
    content_type: str
    size_bytes: int
    status: KnowledgeFileStatus
    title: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_count: int = 0
    error_message: str = ""
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseDetailPayload(KnowledgeBasePayload):
    files: list[KnowledgeFilePayload] = Field(default_factory=list)


class KnowledgeBaseListPayload(BaseModel):
    items: list[KnowledgeBasePayload]
    paging: dict[str, Any]


class KnowledgeFileListPayload(BaseModel):
    items: list[KnowledgeFilePayload]
    paging: dict[str, Any]


class FileUploadPlaceholderRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = "application/pdf"
    size_bytes: int = Field(default=0, ge=0)
    source_uri: str = ""
    title: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArxivImportPlaceholderRequest(BaseModel):
    arxiv_id: str = Field(min_length=1, max_length=64)
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    pdf_url: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationKnowledgeBindingRequest(BaseModel):
    knowledge_base_ids: list[str] = Field(default_factory=list)


class ConversationKnowledgeBindingPayload(BaseModel):
    conversation_id: str
    knowledge_base_ids: list[str]
    updated_at: datetime
