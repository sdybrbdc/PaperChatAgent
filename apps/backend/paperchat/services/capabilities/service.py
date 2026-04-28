from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from paperchat.api.errcode import AppError
from paperchat.database.models.tables import PaperChatToolInvocationLogRecord
from paperchat.database.sql import db_session
from paperchat.services.agent_repository import utcnow
from paperchat.services.agents import agent_service
from paperchat.services.mcp import mcp_service
from paperchat.services.rag import rag_service
from paperchat.services.skills import skill_service


@dataclass(frozen=True)
class Capability:
    key: str
    kind: str
    name: str
    description: str
    status: str = "available"
    input_schema: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityRegistry:
    def list(self, *, user_id: str) -> list[Capability]:
        return [
            *self._rag_capabilities(),
            *self._mcp_capabilities(user_id=user_id),
            *self._skill_capabilities(user_id=user_id),
            *self._agent_capabilities(user_id=user_id),
        ]

    def get(self, *, user_id: str, key: str) -> Capability | None:
        return next((item for item in self.list(user_id=user_id) if item.key == key), None)

    def _rag_capabilities(self) -> list[Capability]:
        return [
            Capability(
                key="rag.retrieve",
                kind="rag",
                name="知识库检索",
                description="从项目知识库检索论文、片段或结构化研究材料。",
                status="available",
                input_schema={"query": "string", "top_k": "integer"},
            ),
            Capability(
                key="rag.temporary_knowledge_base_write",
                kind="rag",
                name="临时知识库写入",
                description="把本次任务中抽取的论文材料写入临时知识库。",
                status="placeholder",
                input_schema={"documents": "array"},
            ),
        ]

    def _mcp_capabilities(self, *, user_id: str) -> list[Capability]:
        tools = mcp_service.list_tools_payload(user_id).get("items", [])
        if tools:
            return [
                Capability(
                    key=item.get("capability_id", f"mcp.{item.get('server_id')}.{item.get('tool_name')}"),
                    kind="mcp",
                    name=item.get("display_name") or item.get("tool_name", ""),
                    description=item.get("description", ""),
                    status=item.get("status", "active"),
                    input_schema=item.get("input_schema", {}),
                    metadata=item,
                )
                for item in tools
            ]
        return [
            Capability(
                key="mcp.search",
                kind="mcp",
                name="MCP 搜索工具",
                description="通过外部 MCP 工具执行搜索或资源发现。",
                status="placeholder",
                input_schema={"query": "string"},
            ),
            Capability(
                key="mcp.fetch",
                kind="mcp",
                name="MCP 资源读取",
                description="读取外部 MCP 资源内容并返回结构化结果。",
                status="placeholder",
                input_schema={"uri": "string"},
            ),
        ]

    def _skill_capabilities(self, *, user_id: str) -> list[Capability]:
        skills = skill_service.list_skills_payload(user_id).get("items", [])
        if skills:
            return [
                Capability(
                    key=f"skill.{item.get('id')}",
                    kind="skill",
                    name=item.get("name", ""),
                    description=item.get("description", ""),
                    status=item.get("status", "disabled"),
                    input_schema=item.get("input_schema", {}),
                    metadata=item,
                )
                for item in skills
            ]
        return [
            Capability(
                key="skill.paper_analysis",
                kind="skill",
                name="论文分析技能",
                description="执行论文聚类、深读、全局分析等技能化步骤。",
                status="placeholder",
                input_schema={"papers": "array", "instruction": "string"},
            ),
            Capability(
                key="skill.report_writing",
                kind="skill",
                name="报告写作技能",
                description="根据分析结果生成章节、综述或研究报告。",
                status="placeholder",
                input_schema={"outline": "array", "materials": "object"},
            ),
        ]

    def _agent_capabilities(self, *, user_id: str) -> list[Capability]:
        workflows = agent_service.list_workflows_payload(user_id).get("items", [])
        return [
            Capability(
                key=f"agent.workflow.{workflow['slug'] or workflow['id']}",
                kind="agent",
                name=workflow.get("name", ""),
                description=workflow.get("description", ""),
                status=workflow.get("status", "available"),
                input_schema={"topic": "string", "max_papers": "integer"},
                metadata={
                    "workflow_id": workflow.get("id"),
                    "slug": workflow.get("slug"),
                    "version": workflow.get("version"),
                    "node_count": workflow.get("node_count"),
                },
            )
            for workflow in workflows
        ]


class CapabilityExecutionLogStore:
    def __init__(self, *, max_items: int = 500) -> None:
        self._items: deque[dict[str, Any]] = deque(maxlen=max_items)

    def append(self, item: dict[str, Any]) -> dict[str, Any]:
        self._items.appendleft(item)
        return item

    def list(self, *, user_id: str, capability_key: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        items = [item for item in self._items if item.get("user_id") == user_id]
        if capability_key:
            items = [item for item in items if item.get("capability_key") == capability_key]
        return items[:limit]


class CapabilityService:
    def __init__(self) -> None:
        self.registry = CapabilityRegistry()
        self.logs = CapabilityExecutionLogStore()

    def list_capabilities_payload(self, *, user_id: str, kind: str | None = None) -> dict[str, Any]:
        items = [asdict(item) for item in self.registry.list(user_id=user_id)]
        if kind:
            items = [item for item in items if item["kind"] == kind]
        summary = {
            "rag": sum(1 for item in items if item["kind"] == "rag"),
            "mcp": sum(1 for item in items if item["kind"] == "mcp"),
            "skill": sum(1 for item in items if item["kind"] == "skill"),
            "agent": sum(1 for item in items if item["kind"] == "agent"),
        }
        return {"items": items, "summary": summary}

    def get_capability_payload(self, *, user_id: str, capability_key: str) -> dict[str, Any]:
        capability = self._require_capability(user_id=user_id, capability_key=capability_key)
        return asdict(capability)

    async def execute_capability_payload(
        self,
        *,
        user_id: str,
        capability_key: str,
        input_payload: dict[str, Any],
        context: dict[str, Any],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        capability = self._require_capability(user_id=user_id, capability_key=capability_key)
        started_at = utcnow()
        log = self._log(
            user_id=user_id,
            capability_key=capability.key,
            kind=capability.kind,
            status="running",
            input_payload=input_payload,
            output_payload={},
            context=context,
            started_at=started_at,
            completed_at=None,
            error=None,
        )
        try:
            output = await self._execute_capability(
                user_id=user_id,
                capability=capability,
                input_payload=input_payload,
                context=context,
                dry_run=dry_run,
            )
        except Exception as exc:
            completed_at = utcnow()
            self._log(
                user_id=user_id,
                capability_key=capability.key,
                kind=capability.kind,
                status="failed",
                input_payload=input_payload,
                output_payload={},
                context={**context, "previous_log_id": log["id"]},
                started_at=started_at,
                completed_at=completed_at,
                error={"message": str(exc), "type": exc.__class__.__name__},
            )
            raise

        completed_log = self._log(
            user_id=user_id,
            capability_key=capability.key,
            kind=capability.kind,
            status="succeeded",
            input_payload=input_payload,
            output_payload=output,
            context={**context, "previous_log_id": log["id"]},
            started_at=started_at,
            completed_at=utcnow(),
            error=None,
        )
        return {"result": output, "log": completed_log}

    async def _execute_capability(
        self,
        *,
        user_id: str,
        capability: Capability,
        input_payload: dict[str, Any],
        context: dict[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
        if capability.key == "rag.retrieve" and not dry_run:
            return rag_service.retrieve_payload(
                user_id=user_id,
                query=str(input_payload.get("query") or ""),
                knowledge_base_ids=list(input_payload.get("knowledge_base_ids") or []),
                conversation_id=context.get("conversation_id"),
                top_k=int(input_payload.get("top_k") or 8),
                metadata_filter=dict(input_payload.get("metadata_filter") or {}),
            )
        if capability.kind == "mcp" and capability.metadata and not dry_run:
            arguments = (
                input_payload.get("arguments")
                if set(input_payload.keys()) <= {"arguments"} and isinstance(input_payload.get("arguments"), dict)
                else input_payload
            )
            return await mcp_service.call_tool_payload(
                user_id=user_id,
                service_id=str(capability.metadata.get("service_id") or capability.metadata.get("server_id") or ""),
                tool_name=str(capability.metadata.get("tool_name") or capability.name),
                arguments=dict(arguments or {}),
            )
        if capability.kind == "skill" and capability.key.startswith("skill."):
            return skill_service.execute_skill_payload(
                user_id=user_id,
                skill_id=capability.key.removeprefix("skill."),
                input_payload=input_payload,
                context=context,
                dry_run=dry_run,
            )
        return {
            "placeholder": True,
            "dry_run": dry_run,
            "capability": asdict(capability),
            "message": "Capability executor is registered, but the concrete runtime is not connected yet.",
        }

    def list_logs_payload(
        self,
        *,
        user_id: str,
        capability_key: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        return {"items": self.logs.list(user_id=user_id, capability_key=capability_key, limit=limit)}

    def _require_capability(self, *, user_id: str, capability_key: str) -> Capability:
        capability = self.registry.get(user_id=user_id, key=capability_key)
        if capability is None:
            raise AppError(status_code=404, code="CAPABILITY_NOT_FOUND", message="能力不存在")
        return capability

    def _log(
        self,
        *,
        user_id: str,
        capability_key: str,
        kind: str,
        status: str,
        input_payload: dict[str, Any],
        output_payload: dict[str, Any],
        context: dict[str, Any],
        started_at: datetime,
        completed_at: datetime | None,
        error: dict[str, Any] | None,
    ) -> dict[str, Any]:
        item = self.logs.append(
            {
                "id": str(uuid4()),
                "user_id": user_id,
                "capability_key": capability_key,
                "kind": kind,
                "status": status,
                "input": input_payload,
                "output": output_payload,
                "context": context,
                "error": error or {},
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat() if completed_at else None,
                "created_at": utcnow().isoformat(),
            }
        )
        if status != "running":
            with db_session() as session:
                session.add(
                    PaperChatToolInvocationLogRecord(
                        user_id=user_id,
                        conversation_id=context.get("conversation_id"),
                        task_id=context.get("task_id"),
                        capability_id=capability_key,
                        capability_type=kind,
                        input_json=input_payload,
                        output_json=output_payload,
                        latency_ms=int((completed_at - started_at).total_seconds() * 1000) if completed_at else 0,
                        status="success" if status == "succeeded" else status,
                        error_text=str((error or {}).get("message", "")),
                    )
                )
        return item


capability_service = CapabilityService()
