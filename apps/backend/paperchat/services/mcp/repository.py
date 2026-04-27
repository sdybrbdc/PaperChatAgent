from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import asc, select

from paperchat.database.sql import db_session


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: Any) -> str | None:
    return value.isoformat() if value else None


MCP_SERVER_TABLE = "paperchat_mcp_servers"
MCP_TOOL_TABLE = "paperchat_mcp_tools"
MCP_SERVER_RECORD = "PaperChatMcpServerRecord"
MCP_TOOL_RECORD = "PaperChatMcpToolRecord"


def _mcp_records():
    from paperchat.database.models import tables

    return getattr(tables, MCP_SERVER_RECORD, None), getattr(tables, MCP_TOOL_RECORD, None)


def _server_payload(record: Any) -> dict[str, Any]:
    env = dict(getattr(record, "env_json", None) or {})
    secret_config = dict(getattr(record, "secret_config_json", None) or {})
    return {
        "id": record.id,
        "user_id": record.user_id,
        "name": record.name,
        "description": record.description,
        "transport_type": record.transport_type,
        "command": record.command,
        "args": list(record.args_json or []),
        "endpoint_url": record.endpoint_url,
        "headers": dict(record.headers_json or {}),
        "env": env,
        "env_keys": sorted(env.keys()),
        "secret_config": secret_config,
        "has_secret_config": bool(secret_config),
        "status": record.status,
        "last_health_status": record.last_health_status,
        "last_checked_at": iso(record.last_checked_at),
        "created_at": iso(record.created_at),
        "updated_at": iso(record.updated_at),
    }


def _tool_payload(record: Any, server_name: str = "") -> dict[str, Any]:
    return {
        "id": record.id,
        "server_id": record.server_id,
        "server_name": server_name,
        "capability_id": f"mcp.{record.server_id}.{record.tool_name}",
        "tool_name": record.tool_name,
        "display_name": record.display_name,
        "description": record.description,
        "input_schema": dict(record.input_schema_json or {}),
        "status": record.status,
        "last_seen_at": iso(record.last_seen_at),
        "created_at": iso(record.created_at),
        "updated_at": iso(record.updated_at),
    }


class SQLMcpRepository:
    @property
    def available(self) -> bool:
        server_record, tool_record = _mcp_records()
        return server_record is not None and tool_record is not None

    def _require_records(self):
        server_record, tool_record = _mcp_records()
        if server_record is None or tool_record is None:
            raise RuntimeError(f"ORM records {MCP_SERVER_RECORD}/{MCP_TOOL_RECORD} are not registered yet")
        return server_record, tool_record

    def list_services(self, user_id: str) -> list[dict[str, Any]]:
        server_record, _tool_record = self._require_records()
        with db_session() as session:
            records = session.scalars(
                select(server_record)
                .where(server_record.user_id == user_id, server_record.status != "deleted")
                .order_by(asc(server_record.created_at))
            )
            return [_server_payload(record) for record in records]

    def create_service(self, user_id: str, values: dict[str, Any]) -> dict[str, Any]:
        server_record, _tool_record = self._require_records()
        with db_session() as session:
            record = server_record(
                user_id=user_id,
                name=values["name"],
                description=values.get("description", ""),
                transport_type=values.get("transport_type", "stdio"),
                command=values.get("command", ""),
                args_json=values.get("args", []),
                endpoint_url=values.get("endpoint_url", ""),
                headers_json=values.get("headers", {}),
                env_json=values.get("env", {}),
                secret_config_json=values.get("secret_config", {}),
                status=values.get("status", "disabled"),
            )
            session.add(record)
            session.flush()
            return _server_payload(record)

    def get_service(self, user_id: str, service_id: str) -> dict[str, Any] | None:
        server_record, _tool_record = self._require_records()
        with db_session() as session:
            record = session.get(server_record, service_id)
            if record is None or record.user_id != user_id or record.status == "deleted":
                return None
            return _server_payload(record)

    def update_service(self, user_id: str, service_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        server_record, _tool_record = self._require_records()
        column_map = {
            "args": "args_json",
            "headers": "headers_json",
            "env": "env_json",
            "secret_config": "secret_config_json",
        }
        with db_session() as session:
            record = session.get(server_record, service_id)
            if record is None or record.user_id != user_id or record.status == "deleted":
                return None
            for key, value in values.items():
                setattr(record, column_map.get(key, key), value)
            record.updated_at = utcnow()
            session.flush()
            return _server_payload(record)

    def delete_service(self, user_id: str, service_id: str) -> bool:
        deleted = self.update_service(user_id, service_id, {"status": "deleted"})
        return deleted is not None

    def set_health(self, user_id: str, service_id: str, status: str) -> dict[str, Any] | None:
        return self.update_service(
            user_id,
            service_id,
            {"last_health_status": status, "last_checked_at": utcnow()},
        )

    def list_tools(self, user_id: str, service_id: str | None = None, enabled_only: bool = True) -> list[dict[str, Any]]:
        server_record, tool_record = self._require_records()
        with db_session() as session:
            query = select(tool_record, server_record.name).join(server_record, tool_record.server_id == server_record.id)
            query = query.where(server_record.user_id == user_id, server_record.status != "deleted")
            if enabled_only:
                query = query.where(server_record.status == "enabled", tool_record.status == "active")
            if service_id:
                query = query.where(tool_record.server_id == service_id)
            query = query.order_by(asc(server_record.name), asc(tool_record.tool_name))
            return [_tool_payload(tool, server_name) for tool, server_name in session.execute(query).all()]

    def replace_tools(self, user_id: str, service_id: str, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        server_record, tool_record = self._require_records()
        with db_session() as session:
            server = session.get(server_record, service_id)
            if server is None or server.user_id != user_id or server.status == "deleted":
                return []
            existing = {
                tool.tool_name: tool
                for tool in session.scalars(select(tool_record).where(tool_record.server_id == service_id))
            }
            seen: set[str] = set()
            for item in tools:
                tool_name = item["tool_name"]
                seen.add(tool_name)
                record = existing.get(tool_name)
                if record is None:
                    record = tool_record(server_id=service_id, tool_name=tool_name)
                    session.add(record)
                record.display_name = item.get("display_name") or tool_name
                record.description = item.get("description", "")
                record.input_schema_json = item.get("input_schema", {})
                record.status = item.get("status", "active")
                record.last_seen_at = utcnow()
                record.updated_at = utcnow()
            for tool_name, record in existing.items():
                if tool_name not in seen:
                    record.status = "disabled"
                    record.updated_at = utcnow()
            session.flush()
            records = session.scalars(
                select(tool_record)
                .where(tool_record.server_id == service_id)
                .order_by(asc(tool_record.tool_name))
            )
            return [_tool_payload(record, server.name) for record in records]


class InMemoryMcpRepository:
    def __init__(self) -> None:
        self._servers: dict[str, dict[str, Any]] = {}
        self._tools: dict[str, dict[str, Any]] = {}

    def list_services(self, user_id: str) -> list[dict[str, Any]]:
        return [
            self._public_server(record)
            for record in sorted(self._servers.values(), key=lambda item: item["created_at"] or "")
            if record["user_id"] == user_id and record["status"] != "deleted"
        ]

    def create_service(self, user_id: str, values: dict[str, Any]) -> dict[str, Any]:
        now = utcnow().isoformat()
        record = {
            "id": str(uuid4()),
            "user_id": user_id,
            "name": values["name"],
            "description": values.get("description", ""),
            "transport_type": values.get("transport_type", "stdio"),
            "command": values.get("command", ""),
            "args": values.get("args", []),
            "endpoint_url": values.get("endpoint_url", ""),
            "headers": values.get("headers", {}),
            "env": values.get("env", {}),
            "secret_config": values.get("secret_config", {}),
            "status": values.get("status", "disabled"),
            "last_health_status": "unknown",
            "last_checked_at": None,
            "created_at": now,
            "updated_at": now,
        }
        self._servers[record["id"]] = record
        return self._public_server(record)

    def get_service(self, user_id: str, service_id: str) -> dict[str, Any] | None:
        record = self._servers.get(service_id)
        if record is None or record["user_id"] != user_id or record["status"] == "deleted":
            return None
        return self._public_server(record)

    def update_service(self, user_id: str, service_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        record = self._servers.get(service_id)
        if record is None or record["user_id"] != user_id or record["status"] == "deleted":
            return None
        record.update(values)
        record["updated_at"] = utcnow().isoformat()
        return self._public_server(record)

    def delete_service(self, user_id: str, service_id: str) -> bool:
        return self.update_service(user_id, service_id, {"status": "deleted"}) is not None

    def set_health(self, user_id: str, service_id: str, status: str) -> dict[str, Any] | None:
        return self.update_service(
            user_id,
            service_id,
            {"last_health_status": status, "last_checked_at": utcnow().isoformat()},
        )

    def list_tools(self, user_id: str, service_id: str | None = None, enabled_only: bool = True) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for tool in self._tools.values():
            server = self._servers.get(tool["server_id"])
            if server is None or server["user_id"] != user_id or server["status"] == "deleted":
                continue
            if service_id and tool["server_id"] != service_id:
                continue
            if enabled_only and (server["status"] != "enabled" or tool["status"] != "active"):
                continue
            items.append(self._public_tool(tool, server["name"]))
        return sorted(items, key=lambda item: (item["server_name"], item["tool_name"]))

    def replace_tools(self, user_id: str, service_id: str, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        server = self._servers.get(service_id)
        if server is None or server["user_id"] != user_id or server["status"] == "deleted":
            return []
        existing = {tool["tool_name"]: tool for tool in self._tools.values() if tool["server_id"] == service_id}
        seen: set[str] = set()
        now = utcnow().isoformat()
        for item in tools:
            tool_name = item["tool_name"]
            seen.add(tool_name)
            record = existing.get(tool_name)
            if record is None:
                record = {
                    "id": str(uuid4()),
                    "server_id": service_id,
                    "tool_name": tool_name,
                    "created_at": now,
                }
                self._tools[record["id"]] = record
            record.update(
                {
                    "display_name": item.get("display_name") or tool_name,
                    "description": item.get("description", ""),
                    "input_schema": item.get("input_schema", {}),
                    "status": item.get("status", "active"),
                    "last_seen_at": now,
                    "updated_at": now,
                }
            )
        for tool_name, record in existing.items():
            if tool_name not in seen:
                record["status"] = "disabled"
                record["updated_at"] = now
        return self.list_tools(user_id, service_id=service_id, enabled_only=False)

    def _public_server(self, record: dict[str, Any]) -> dict[str, Any]:
        env = dict(record.get("env") or {})
        secret_config = dict(record.get("secret_config") or {})
        return {
            **record,
            "env_keys": sorted(env.keys()),
            "has_secret_config": bool(secret_config),
        }

    def _public_tool(self, record: dict[str, Any], server_name: str = "") -> dict[str, Any]:
        return {
            **record,
            "server_name": server_name,
            "capability_id": f"mcp.{record['server_id']}.{record['tool_name']}",
            "input_schema": dict(record.get("input_schema") or {}),
        }
