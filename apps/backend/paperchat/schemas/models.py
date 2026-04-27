from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ModelProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    provider_type: str = Field(default="openai_compatible", min_length=1, max_length=64)
    base_url: str = Field(default="", max_length=512)
    api_key_ref: str = Field(default="", max_length=255)
    status: str = Field(default="active", max_length=32)
    config: dict[str, Any] = Field(default_factory=dict)


class ModelProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    provider_type: str | None = Field(default=None, min_length=1, max_length=64)
    base_url: str | None = Field(default=None, max_length=512)
    api_key_ref: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=32)
    config: dict[str, Any] | None = None


class ModelRouteCreate(BaseModel):
    provider_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=128)
    model_name: str = Field(min_length=1, max_length=128)
    model_type: str = Field(default="chat", max_length=32)
    priority: int = Field(default=100, ge=0, le=10000)
    status: str = Field(default="active", max_length=32)
    is_default: bool = False
    config: dict[str, Any] = Field(default_factory=dict)


class ModelRouteUpdate(BaseModel):
    provider_id: str | None = Field(default=None, min_length=1, max_length=36)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    model_name: str | None = Field(default=None, min_length=1, max_length=128)
    model_type: str | None = Field(default=None, max_length=32)
    priority: int | None = Field(default=None, ge=0, le=10000)
    status: str | None = Field(default=None, max_length=32)
    is_default: bool | None = None
    config: dict[str, Any] | None = None


class ModelRouteTestRequest(BaseModel):
    prompt: str = Field(default="ping", max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelUsageLogCreate(BaseModel):
    provider_id: str | None = Field(default=None, max_length=36)
    route_id: str | None = Field(default=None, max_length=36)
    conversation_id: str | None = Field(default=None, max_length=36)
    workflow_run_id: str | None = Field(default=None, max_length=36)
    task_id: str | None = Field(default=None, max_length=36)
    tool_name: str = Field(default="", max_length=128)
    model_name: str = Field(default="", max_length=128)
    operation: str = Field(default="chat_completion", max_length=64)
    status: str = Field(default="success", max_length=32)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    error_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
