from __future__ import annotations

import asyncio
import json
import shlex
from typing import Any

from paperchat.api.errcode import AppError
from paperchat.schemas.mcp import McpServiceCreate, McpServiceImportRequest, McpServiceUpdate
from paperchat.services.cc_switch import cc_switch_discovery
from paperchat.services.mcp.repository import InMemoryMcpRepository, SQLMcpRepository
from paperchat.services.mcp.runtime import mcp_runtime


class McpService:
    def __init__(self) -> None:
        self._sql_repository = SQLMcpRepository()
        self._memory_repository = InMemoryMcpRepository()

    @property
    def repository(self):
        return self._sql_repository if self._sql_repository.available else self._memory_repository

    def list_services_payload(self, user_id: str) -> dict[str, Any]:
        return {"items": [self._service_payload(item) for item in self.repository.list_services(user_id)]}

    def list_cc_switch_services_payload(self) -> dict[str, Any]:
        return {
            "source": cc_switch_discovery.source_payload(),
            "items": [self._discovered_service_payload(item) for item in cc_switch_discovery.discover_mcp_servers()],
        }

    async def sync_cc_switch_services_payload(self, user_id: str) -> dict[str, Any]:
        discovered = cc_switch_discovery.discover_mcp_servers()
        existing = self.repository.list_services(user_id)
        created = 0
        updated = 0
        refreshed = 0
        refresh_errors: list[dict[str, Any]] = []
        items: list[dict[str, Any]] = []
        for item in discovered:
            match = self._find_existing_cc_switch_service(existing, item)
            values = {
                "name": item["name"],
                "description": item["description"],
                "transport_type": item["transport_type"],
                "command": item["command"],
                "args": item["args"],
                "endpoint_url": item["endpoint_url"],
                "headers": item["headers"],
                "env": item["env"],
                "secret_config": item["secret_config"],
                "status": item["status"],
            }
            if match:
                record = self.repository.update_service(user_id, match["id"], values) or match
                updated += 1
            else:
                record = self.repository.create_service(user_id, values)
                created += 1
            if record.get("status") == "enabled":
                try:
                    refresh_payload = await self.refresh_tools_payload(user_id, record["id"])
                    if refresh_payload.get("ok"):
                        refreshed += 1
                except Exception as exc:
                    refresh_errors.append(
                        {"service_id": record["id"], "name": record.get("name", ""), "message": str(exc)}
                    )
            items.append(self._service_payload(record))
        return {
            "source": cc_switch_discovery.source_payload(),
            "created": created,
            "updated": updated,
            "refreshed": refreshed,
            "refresh_errors": refresh_errors,
            "total": len(items),
            "items": items,
        }

    def create_service_payload(self, user_id: str, payload: McpServiceCreate) -> dict[str, Any]:
        record = self.repository.create_service(user_id, payload.model_dump())
        return self._service_payload(record)

    async def import_services_payload(self, user_id: str, payload: McpServiceImportRequest) -> dict[str, Any]:
        services = self._extract_import_services(payload.config, default_status=payload.status)
        if not services:
            raise AppError(status_code=400, code="MCP_IMPORT_EMPTY", message="未识别到可导入的 MCP 服务配置")

        existing = self.repository.list_services(user_id)
        created = 0
        updated = 0
        refreshed = 0
        refresh_errors: list[dict[str, Any]] = []
        items: list[dict[str, Any]] = []

        for service_config in services:
            match = self._find_existing_import_service(existing, service_config)
            if match and payload.overwrite_existing:
                record = self.repository.update_service(user_id, match["id"], service_config) or match
                updated += 1
            elif match:
                record = match
            else:
                record = self.repository.create_service(user_id, service_config)
                created += 1

            if payload.refresh_tools and record.get("status") == "enabled":
                try:
                    refresh_payload = await self.refresh_tools_payload(user_id, record["id"])
                    if refresh_payload.get("ok"):
                        refreshed += 1
                except Exception as exc:
                    refresh_errors.append(
                        {"service_id": record["id"], "name": record.get("name", ""), "message": str(exc)}
                    )
            items.append(self._service_payload(record))

        return {
            "created": created,
            "updated": updated,
            "refreshed": refreshed,
            "refresh_errors": refresh_errors,
            "total": len(items),
            "items": items,
        }

    def get_service_payload(self, user_id: str, service_id: str) -> dict[str, Any]:
        record = self._require_service(user_id, service_id)
        tools = self.repository.list_tools(user_id, service_id=service_id, enabled_only=False)
        return {**self._service_payload(record), "tools": [self._tool_payload(item) for item in tools]}

    def update_service_payload(self, user_id: str, service_id: str, payload: McpServiceUpdate) -> dict[str, Any]:
        changes = payload.model_dump(exclude_unset=True)
        record = self.repository.update_service(user_id, service_id, changes)
        if record is None:
            raise AppError(status_code=404, code="MCP_SERVICE_NOT_FOUND", message="MCP 服务不存在")
        return self._service_payload(record)

    def delete_service_payload(self, user_id: str, service_id: str) -> dict[str, Any]:
        if not self.repository.delete_service(user_id, service_id):
            raise AppError(status_code=404, code="MCP_SERVICE_NOT_FOUND", message="MCP 服务不存在")
        return {"deleted": True, "id": service_id}

    async def test_service_payload(self, user_id: str, service_id: str) -> dict[str, Any]:
        record = self._require_service(user_id, service_id)
        ok, message = self._validate_service_config(record)
        details: dict[str, Any] = {
            "transport_type": record["transport_type"],
            "external_connection": "not_attempted",
        }
        if not ok:
            self.repository.set_health(user_id, service_id, "unhealthy")
            return {"ok": False, "status": "unhealthy", "message": message, "details": details}
        try:
            tools = await asyncio.wait_for(mcp_runtime.list_tools(record), timeout=self._runtime_timeout(record))
        except Exception as exc:
            self.repository.set_health(user_id, service_id, "unhealthy")
            return {
                "ok": False,
                "status": "unhealthy",
                "message": f"MCP 服务连接失败：{exc}",
                "details": {**details, "external_connection": "failed"},
            }
        self.repository.set_health(user_id, service_id, "healthy")
        return {
            "ok": True,
            "status": "healthy",
            "message": f"MCP 服务连接成功，发现 {len(tools)} 个工具",
            "details": {**details, "external_connection": "connected", "tool_count": len(tools)},
        }

    async def refresh_tools_payload(self, user_id: str, service_id: str) -> dict[str, Any]:
        record = self._require_service(user_id, service_id)
        ok, message = self._validate_service_config(record)
        if not ok:
            self.repository.set_health(user_id, service_id, "unhealthy")
            return {"ok": False, "refreshed": False, "tools": [], "message": message}
        try:
            discovered_tools = await asyncio.wait_for(
                mcp_runtime.list_tools(record),
                timeout=self._runtime_timeout(record),
            )
        except Exception as exc:
            self.repository.set_health(user_id, service_id, "unhealthy")
            return {"ok": False, "refreshed": False, "tools": [], "message": f"MCP tools refresh failed: {exc}"}
        self.repository.set_health(user_id, service_id, "healthy")
        tools = self.repository.replace_tools(user_id, service_id, discovered_tools)
        return {
            "ok": True,
            "refreshed": True,
            "tools": [self._tool_payload(item) for item in tools],
            "message": f"已从 MCP 服务发现 {len(discovered_tools)} 个工具",
        }

    def list_tools_payload(self, user_id: str) -> dict[str, Any]:
        return {"items": [self._tool_payload(item) for item in self.repository.list_tools(user_id)]}

    async def call_tool_payload(
        self,
        *,
        user_id: str,
        service_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = self._require_service(user_id, service_id)
        ok, message = self._validate_service_config(record)
        if not ok:
            raise AppError(status_code=400, code="MCP_SERVICE_INVALID", message=message)
        result = await asyncio.wait_for(
            mcp_runtime.call_tool(record, tool_name=tool_name, arguments=arguments or {}),
            timeout=self._runtime_timeout(record),
        )
        if result.get("is_error"):
            raise AppError(
                status_code=502,
                code="MCP_TOOL_FAILED",
                message=str(result.get("text") or f"MCP 工具 {tool_name} 执行失败"),
            )
        return {
            "service": self._service_payload(record),
            "tool_name": tool_name,
            "arguments": arguments or {},
            "result": result,
        }

    def _require_service(self, user_id: str, service_id: str) -> dict[str, Any]:
        record = self.repository.get_service(user_id, service_id)
        if record is None:
            raise AppError(status_code=404, code="MCP_SERVICE_NOT_FOUND", message="MCP 服务不存在")
        return record

    def _find_existing_cc_switch_service(
        self,
        existing: list[dict[str, Any]],
        discovered: dict[str, Any],
    ) -> dict[str, Any] | None:
        cc_switch_id = discovered.get("cc_switch_id")
        for item in existing:
            secret_config = item.get("secret_config") or {}
            if secret_config.get("source") == "cc-switch" and secret_config.get("cc_switch_id") == cc_switch_id:
                return item
            if item.get("name") == discovered.get("name") and secret_config.get("source") == "cc-switch":
                return item
        return None

    def _find_existing_import_service(
        self,
        existing: list[dict[str, Any]],
        imported: dict[str, Any],
    ) -> dict[str, Any] | None:
        import_name = (imported.get("secret_config") or {}).get("import_name")
        for item in existing:
            secret_config = item.get("secret_config") or {}
            if import_name and secret_config.get("source") == "json-import" and secret_config.get("import_name") == import_name:
                return item
            if item.get("name") == imported.get("name"):
                return item
        return None

    def _extract_import_services(self, config: Any, *, default_status: str) -> list[dict[str, Any]]:
        data = self._parse_import_config(config)
        entries: list[tuple[str, Any]] = []
        if isinstance(data, dict) and isinstance(data.get("mcpServers"), dict):
            entries = [(str(name), value) for name, value in data["mcpServers"].items()]
        elif isinstance(data, dict) and isinstance(data.get("servers"), dict):
            entries = [(str(name), value) for name, value in data["servers"].items()]
        elif isinstance(data, dict) and isinstance(data.get("servers"), list):
            entries = [
                (str(item.get("name") or item.get("id") or f"mcp-{index + 1}"), item)
                for index, item in enumerate(data["servers"])
                if isinstance(item, dict)
            ]
        elif isinstance(data, dict) and self._looks_like_single_service(data):
            entries = [(str(data.get("name") or data.get("id") or "MCP Server"), data)]
        elif isinstance(data, dict):
            entries = [(str(name), value) for name, value in data.items() if isinstance(value, dict)]

        services: list[dict[str, Any]] = []
        for name, raw_config in entries:
            if not isinstance(raw_config, dict):
                continue
            services.append(self._normalize_import_service(name, raw_config, default_status=default_status))
        return services

    def _parse_import_config(self, config: Any) -> Any:
        if isinstance(config, str):
            try:
                return json.loads(config)
            except json.JSONDecodeError as exc:
                raise AppError(status_code=400, code="MCP_IMPORT_JSON_INVALID", message=f"JSON 格式不正确：{exc}") from exc
        return config

    def _looks_like_single_service(self, data: dict[str, Any]) -> bool:
        keys = {
            "name",
            "type",
            "transport",
            "transport_type",
            "command",
            "args",
            "url",
            "endpoint_url",
            "headers",
            "env",
        }
        return any(key in data for key in keys)

    def _normalize_import_service(
        self,
        name_hint: str,
        raw_config: dict[str, Any],
        *,
        default_status: str,
    ) -> dict[str, Any]:
        name = str(raw_config.get("name") or raw_config.get("id") or name_hint or "MCP Server").strip()
        if not name:
            raise AppError(status_code=400, code="MCP_IMPORT_NAME_MISSING", message="MCP 服务缺少名称")

        command = str(raw_config.get("command") or "").strip()
        args = self._string_list(raw_config.get("args"))
        if command and not args:
            parts = shlex.split(command)
            if len(parts) > 1:
                command = parts[0]
                args = parts[1:]

        endpoint_url = str(raw_config.get("endpoint_url") or raw_config.get("url") or "").strip()
        transport_type = self._normalize_transport(raw_config, command=command, endpoint_url=endpoint_url)
        if transport_type == "stdio" and not command:
            raise AppError(status_code=400, code="MCP_IMPORT_COMMAND_MISSING", message=f"{name} 缺少 command")
        if transport_type != "stdio" and not endpoint_url:
            raise AppError(status_code=400, code="MCP_IMPORT_URL_MISSING", message=f"{name} 缺少 url 或 endpoint_url")

        enabled = raw_config.get("enabled")
        raw_status = str(raw_config.get("status") or "").strip()
        status = raw_status if raw_status in {"enabled", "disabled"} else default_status
        if enabled is False:
            status = "disabled"

        timeout = raw_config.get("timeout")
        cwd = str(raw_config.get("cwd") or "").strip()
        secret_config = {
            "source": "json-import",
            "import_name": name_hint,
            "timeout": timeout,
            "raw_config": self._redact_import_config(raw_config),
        }
        if cwd:
            secret_config["cwd"] = cwd

        return {
            "name": name,
            "description": str(raw_config.get("description") or ""),
            "transport_type": transport_type,
            "command": command,
            "args": args,
            "endpoint_url": endpoint_url,
            "headers": self._string_dict(raw_config.get("headers")),
            "env": self._string_dict(raw_config.get("env")),
            "secret_config": secret_config,
            "status": status,
        }

    def _normalize_transport(self, raw_config: dict[str, Any], *, command: str, endpoint_url: str) -> str:
        raw = str(
            raw_config.get("transport_type")
            or raw_config.get("transport")
            or raw_config.get("type")
            or ("stdio" if command else "streamable_http" if endpoint_url else "stdio")
        ).strip().lower()
        if raw in {"http", "streamable-http", "streamable_http"}:
            return "streamable_http"
        if raw in {"stdio", "sse", "websocket"}:
            return raw
        raise AppError(status_code=400, code="MCP_IMPORT_TRANSPORT_UNSUPPORTED", message=f"不支持的 MCP 传输类型：{raw}")

    def _string_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str) and value.strip():
            return shlex.split(value)
        return []

    def _string_dict(self, value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        return {str(key): str(item) for key, item in value.items()}

    def _redact_import_config(self, config: dict[str, Any]) -> dict[str, Any]:
        redacted = dict(config)
        if redacted.get("env"):
            redacted["env"] = {key: "***" for key in dict(redacted["env"]).keys()}
        if redacted.get("headers"):
            redacted["headers"] = {key: "***" for key in dict(redacted["headers"]).keys()}
        return redacted

    def _validate_service_config(self, record: dict[str, Any]) -> tuple[bool, str]:
        transport_type = record.get("transport_type", "stdio")
        if transport_type == "stdio" and not str(record.get("command") or "").strip():
            return False, "stdio MCP 服务需要配置 command"
        if transport_type in {"sse", "http", "streamable_http", "websocket"} and not str(record.get("endpoint_url") or "").strip():
            return False, f"{transport_type} MCP 服务需要配置 endpoint_url"
        return True, "MCP 服务配置检查通过"

    def _runtime_timeout(self, record: dict[str, Any]) -> float:
        secret_config = dict(record.get("secret_config") or {})
        try:
            return float(secret_config.get("timeout") or mcp_runtime.default_timeout_seconds)
        except (TypeError, ValueError):
            return mcp_runtime.default_timeout_seconds

    def _service_payload(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record["id"],
            "name": record["name"],
            "description": record.get("description", ""),
            "transport_type": record.get("transport_type", "stdio"),
            "command": record.get("command", ""),
            "args": record.get("args", []),
            "endpoint_url": record.get("endpoint_url", ""),
            "url": record.get("endpoint_url", ""),
            "headers": record.get("headers", {}),
            "env_keys": record.get("env_keys", []),
            "has_secret_config": bool(record.get("has_secret_config")),
            "status": record.get("status", "disabled"),
            "last_health_status": record.get("last_health_status", "unknown"),
            "last_health_message": record.get("last_health_message", ""),
            "tool_count": len(self.repository.list_tools(record.get("user_id", ""), service_id=record["id"], enabled_only=False))
            if record.get("user_id")
            else 0,
            "last_checked_at": record.get("last_checked_at"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
        }

    def _discovered_service_payload(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record["cc_switch_id"],
            "name": record["name"],
            "description": record.get("description", ""),
            "transport_type": record.get("transport_type", "stdio"),
            "command": record.get("command", ""),
            "args": record.get("args", []),
            "endpoint_url": record.get("endpoint_url", ""),
            "url": record.get("endpoint_url", ""),
            "headers": record.get("headers", {}),
            "env_keys": sorted((record.get("env") or {}).keys()),
            "has_secret_config": bool(record.get("secret_config")),
            "status": record.get("status", "disabled"),
            "last_health_status": "unknown",
            "last_health_message": "",
            "tool_count": 0,
            "last_checked_at": None,
            "created_at": None,
            "updated_at": None,
            "metadata": {
                "source": "cc-switch",
                "cc_switch_id": record.get("cc_switch_id"),
                "enabled_apps": (record.get("secret_config") or {}).get("enabled_apps", []),
            },
        }

    def _tool_payload(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record["id"],
            "server_id": record["server_id"],
            "service_id": record["server_id"],
            "server_name": record.get("server_name", ""),
            "service_name": record.get("server_name", ""),
            "capability_id": record.get("capability_id", f"mcp.{record['server_id']}.{record['tool_name']}"),
            "tool_name": record["tool_name"],
            "display_name": record.get("display_name") or record["tool_name"],
            "description": record.get("description", ""),
            "input_schema": record.get("input_schema", {}),
            "status": record.get("status", "active"),
            "enabled": record.get("status", "active") == "active",
            "last_seen_at": record.get("last_seen_at"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
        }


mcp_service = McpService()
