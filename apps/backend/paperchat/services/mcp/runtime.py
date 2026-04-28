from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

from paperchat.api.errcode import AppError


class McpRuntime:
    def __init__(self, *, default_timeout_seconds: float = 20.0) -> None:
        self.default_timeout_seconds = default_timeout_seconds

    async def list_tools(self, service: dict[str, Any]) -> list[dict[str, Any]]:
        async with self._session(service) as session:
            await session.initialize()
            tools = await self._list_all_tools(session)
            return [self._tool_payload(tool) for tool in tools]

    async def call_tool(
        self,
        service: dict[str, Any],
        *,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with self._session(service) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments or {})
            return {
                "tool_name": tool_name,
                "is_error": bool(getattr(result, "isError", False)),
                "content": self._normalize_content_list(getattr(result, "content", [])),
                "text": self._content_text(getattr(result, "content", [])),
                "raw": self._jsonable(result),
            }

    @asynccontextmanager
    async def _session(self, service: dict[str, Any]) -> AsyncIterator[Any]:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.sse import sse_client
            from mcp.client.stdio import stdio_client
            from mcp.client.streamable_http import streamablehttp_client
        except ImportError as exc:
            raise AppError(
                status_code=500,
                code="MCP_SDK_MISSING",
                message="后端缺少 mcp Python SDK，请安装后重试",
            ) from exc

        transport = self._transport(service)
        timeout = self._timeout(service)
        session_kwargs = {"read_timeout_seconds": timedelta(seconds=timeout)}

        if transport == "stdio":
            command = str(service.get("command") or "").strip()
            if not command:
                raise AppError(status_code=400, code="MCP_COMMAND_MISSING", message="stdio MCP 服务缺少 command")
            env = {str(key): str(value) for key, value in dict(service.get("env") or {}).items()}
            env.setdefault("PATH", os.environ.get("PATH", ""))
            params = StdioServerParameters(
                command=command,
                args=[str(item) for item in service.get("args") or []],
                env=env,
                cwd=self._cwd(service),
            )
            async with (
                stdio_client(params) as (read, write),
                ClientSession(read, write, **session_kwargs) as session,
            ):
                yield session
            return

        endpoint_url = str(service.get("endpoint_url") or service.get("url") or "").strip()
        if not endpoint_url:
            raise AppError(status_code=400, code="MCP_URL_MISSING", message=f"{transport} MCP 服务缺少 endpoint_url")

        headers = dict(service.get("headers") or {})
        if transport == "sse":
            async with (
                sse_client(endpoint_url, headers=headers or None, timeout=timeout) as (read, write),
                ClientSession(read, write, **session_kwargs) as session,
            ):
                yield session
            return

        if transport == "streamable_http":
            async with (
                streamablehttp_client(
                    endpoint_url,
                    headers=headers or None,
                    timeout=timedelta(seconds=timeout),
                    sse_read_timeout=timedelta(seconds=max(timeout, 60.0)),
                    terminate_on_close=True,
                ) as (read, write, _),
                ClientSession(read, write, **session_kwargs) as session,
            ):
                yield session
            return

        if transport == "websocket":
            try:
                from mcp.client.websocket import websocket_client
            except ImportError as exc:
                raise AppError(
                    status_code=500,
                    code="MCP_WEBSOCKET_MISSING",
                    message="当前环境缺少 MCP websocket 客户端依赖",
                ) from exc
            async with (
                websocket_client(endpoint_url) as (read, write),
                ClientSession(read, write, **session_kwargs) as session,
            ):
                yield session
            return

        raise AppError(status_code=400, code="MCP_TRANSPORT_UNSUPPORTED", message=f"不支持的 MCP 传输类型：{transport}")

    async def _list_all_tools(self, session: Any) -> list[Any]:
        tools: list[Any] = []
        cursor: str | None = None
        for _ in range(1000):
            page = await session.list_tools(cursor=cursor)
            tools.extend(list(getattr(page, "tools", []) or []))
            cursor = getattr(page, "nextCursor", None)
            if not cursor:
                return tools
        raise AppError(status_code=502, code="MCP_TOOL_LIST_TOO_LARGE", message="MCP 工具列表分页过多")

    def _tool_payload(self, tool: Any) -> dict[str, Any]:
        return {
            "tool_name": str(getattr(tool, "name", "") or ""),
            "display_name": str(getattr(tool, "name", "") or ""),
            "description": str(getattr(tool, "description", "") or ""),
            "input_schema": self._jsonable(getattr(tool, "inputSchema", {}) or {}),
            "status": "active",
        }

    def _transport(self, service: dict[str, Any]) -> str:
        transport = str(service.get("transport_type") or service.get("type") or "stdio").strip().lower()
        if transport in {"http", "streamable-http", "streamable_http"}:
            return "streamable_http"
        return transport

    def _timeout(self, service: dict[str, Any]) -> float:
        secret_config = dict(service.get("secret_config") or {})
        timeout = secret_config.get("timeout")
        try:
            return float(timeout or self.default_timeout_seconds)
        except (TypeError, ValueError):
            return self.default_timeout_seconds

    def _cwd(self, service: dict[str, Any]) -> str | None:
        secret_config = dict(service.get("secret_config") or {})
        raw_config = dict(secret_config.get("raw_config") or {})
        cwd = raw_config.get("cwd") or service.get("cwd")
        return str(cwd) if cwd else None

    def _normalize_content_list(self, content: list[Any]) -> list[dict[str, Any]]:
        return [self._jsonable(item) for item in content]

    def _content_text(self, content: list[Any]) -> str:
        parts: list[str] = []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                parts.append(str(text))
        return "\n".join(parts)

    def _jsonable(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(key): self._jsonable(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._jsonable(item) for item in value]
        if hasattr(value, "model_dump"):
            return self._jsonable(value.model_dump(mode="json"))
        if hasattr(value, "__dict__"):
            return self._jsonable(vars(value))
        return str(value)


mcp_runtime = McpRuntime()
