from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


McpTransportType = Literal["stdio", "sse", "http", "streamable_http", "websocket"]
McpServiceStatus = Literal["enabled", "disabled"]
McpHealthStatus = Literal["unknown", "healthy", "unhealthy"]
McpToolStatus = Literal["active", "disabled"]


class McpServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    transport_type: McpTransportType = "stdio"
    command: str = ""
    args: list[str] = Field(default_factory=list)
    endpoint_url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    env: dict[str, str] = Field(default_factory=dict)
    secret_config: dict[str, Any] = Field(default_factory=dict)
    status: McpServiceStatus = "disabled"


class McpServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    transport_type: McpTransportType | None = None
    command: str | None = None
    args: list[str] | None = None
    endpoint_url: str | None = None
    headers: dict[str, str] | None = None
    env: dict[str, str] | None = None
    secret_config: dict[str, Any] | None = None
    status: McpServiceStatus | None = None


class McpServicePayload(BaseModel):
    id: str
    name: str
    description: str
    transport_type: str
    command: str
    args: list[str]
    endpoint_url: str
    headers: dict[str, str]
    env_keys: list[str]
    has_secret_config: bool
    status: str
    last_health_status: str
    last_checked_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class McpToolPayload(BaseModel):
    id: str
    server_id: str
    server_name: str = ""
    capability_id: str
    tool_name: str
    display_name: str
    description: str
    input_schema: dict[str, Any]
    status: str
    last_seen_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class McpServiceListPayload(BaseModel):
    items: list[McpServicePayload]


class McpServiceDetailPayload(McpServicePayload):
    tools: list[McpToolPayload] = Field(default_factory=list)


class McpToolListPayload(BaseModel):
    items: list[McpToolPayload]


class McpTestPayload(BaseModel):
    ok: bool
    status: McpHealthStatus
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class McpRefreshToolsPayload(BaseModel):
    ok: bool
    refreshed: bool
    tools: list[McpToolPayload] = Field(default_factory=list)
    message: str


class McpToolCallRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)
