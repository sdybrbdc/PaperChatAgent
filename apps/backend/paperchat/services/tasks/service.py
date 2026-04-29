from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from sqlalchemy import desc, select

from paperchat.api.errcode import AppError
from paperchat.database.models.tables import (
    PaperChatResearchTaskRecord,
    PaperChatWorkflowNodeRunRecord,
    PaperChatWorkflowRunRecord,
)
from paperchat.database.sql import db_session
from paperchat.services.agent_repository import agent_repository, utcnow
from paperchat.services.agents import agent_service


TERMINAL_STATUSES = {"completed", "failed", "canceled"}
ACTIVE_STATUSES = {"pending", "running"}


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class TaskService:
    async def create_task_payload(
        self,
        *,
        user_id: str,
        workflow_id: str,
        topic: str,
        conversation_id: str | None,
        max_papers: int,
        start_background: bool,
    ) -> dict[str, Any]:
        run_payload = await agent_service.create_run_payload(
            user_id=user_id,
            workflow_id=workflow_id,
            topic=topic,
            conversation_id=conversation_id,
            max_papers=max_papers,
            start_background=start_background,
        )
        task_id = str(run_payload.get("task_id") or "")
        if task_id:
            return self.get_task_payload(user_id=user_id, task_id=task_id)
        return run_payload

    def list_tasks_payload(
        self,
        *,
        user_id: str,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        with db_session() as session:
            statement = select(PaperChatResearchTaskRecord).where(PaperChatResearchTaskRecord.user_id == user_id)
            if status:
                statement = statement.where(PaperChatResearchTaskRecord.status == status)
            statement = statement.order_by(desc(PaperChatResearchTaskRecord.created_at)).limit(limit).offset(offset)
            tasks = list(session.scalars(statement))
            task_ids = [task.id for task in tasks]
            runs_by_task: dict[str, PaperChatWorkflowRunRecord] = {}
            if task_ids:
                runs = session.scalars(
                    select(PaperChatWorkflowRunRecord)
                    .where(PaperChatWorkflowRunRecord.task_id.in_(task_ids))
                    .order_by(desc(PaperChatWorkflowRunRecord.created_at))
                )
                for run in runs:
                    runs_by_task.setdefault(run.task_id, run)

            return {
                "items": [self._task_payload(task, run=runs_by_task.get(task.id)) for task in tasks],
                "limit": limit,
                "offset": offset,
            }

    def get_task_payload(self, *, user_id: str, task_id: str) -> dict[str, Any]:
        task, run = self._require_task_with_run(user_id=user_id, task_id=task_id)
        return self._task_payload(task, run=run, include_nodes=True, include_artifacts=True, include_run=True)

    def cancel_task_payload(self, *, user_id: str, task_id: str) -> dict[str, Any]:
        task, run = self._require_task_with_run(user_id=user_id, task_id=task_id)
        if task.status in TERMINAL_STATUSES:
            return self.get_task_payload(user_id=user_id, task_id=task_id)

        now = utcnow()
        agent_repository.update_task(
            task.id,
            status="canceled",
            failed_reason="用户已取消任务",
            completed_at=now,
        )
        if run is not None:
            agent_repository.update_run(
                run.id,
                status="canceled",
                error_json={"message": "用户已取消任务"},
                completed_at=now,
            )
            for node in agent_repository.list_node_runs(run.id):
                if node.status in ACTIVE_STATUSES:
                    agent_repository.update_node_run(
                        workflow_run_id=run.id,
                        node_id=node.node_id,
                        status="canceled",
                        error_text="用户已取消任务",
                        completed_at=now,
                    )
        return self.get_task_payload(user_id=user_id, task_id=task_id)

    async def task_event_stream(self, *, user_id: str, task_id: str, request) -> Any:
        from paperchat.api.responses.sse import encode_sse

        last_snapshot = ""
        while True:
            if await request.is_disconnected():
                break
            try:
                payload = self.get_task_payload(user_id=user_id, task_id=task_id)
            except AppError as exc:
                yield encode_sse("task.error", {"code": exc.code, "message": exc.message})
                break

            snapshot = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
            if snapshot != last_snapshot:
                event_name = "task.completed" if payload.get("status") in TERMINAL_STATUSES else "task.snapshot"
                yield encode_sse(event_name, payload)
                last_snapshot = snapshot
                if payload.get("status") in TERMINAL_STATUSES:
                    break
            else:
                yield encode_sse("task.heartbeat", {"task_id": task_id})
            await asyncio.sleep(2)

    def _require_task_with_run(
        self,
        *,
        user_id: str,
        task_id: str,
    ) -> tuple[PaperChatResearchTaskRecord, PaperChatWorkflowRunRecord | None]:
        with db_session() as session:
            task = session.get(PaperChatResearchTaskRecord, task_id)
            if task is None or task.user_id != user_id:
                raise AppError(status_code=404, code="TASK_NOT_FOUND", message="任务不存在")
            run = session.scalar(
                select(PaperChatWorkflowRunRecord)
                .where(PaperChatWorkflowRunRecord.task_id == task.id)
                .order_by(desc(PaperChatWorkflowRunRecord.created_at))
            )
            return task, run

    def _task_payload(
        self,
        task: PaperChatResearchTaskRecord,
        *,
        run: PaperChatWorkflowRunRecord | None,
        include_nodes: bool = False,
        include_artifacts: bool = False,
        include_run: bool = False,
    ) -> dict[str, Any]:
        workflow = agent_repository.get_workflow(task.workflow_id)
        payload = {
            "id": task.id,
            "run_id": run.id if run else None,
            "workflow_id": task.workflow_id,
            "workflow_name": workflow.name if workflow else "",
            "conversation_id": task.conversation_id,
            "title": task.title,
            "status": task.status,
            "current_node": task.current_node,
            "progress": task.progress,
            "summary": task.summary,
            "failed_reason": task.failed_reason,
            "detail_url": f"/tasks/{task.id}",
            "payload": run.input_json if run else {},
            "input": run.input_json if run else {},
            "output": run.output_json if run else {},
            "error": run.error_json if run else {},
            "created_at": _dt(task.created_at),
            "updated_at": _dt(task.updated_at),
            "started_at": _dt(run.started_at) if run else None,
            "completed_at": _dt(task.completed_at),
            "agent_detail_url": f"/agents/runs/{run.id}" if run else "",
        }
        if run:
            payload.update(
                {
                    "run_status": run.status,
                    "run_current_node": run.current_node,
                    "input": run.input_json or {},
                    "output": run.output_json or {},
                    "error": run.error_json or {},
                    "agent_detail_url": f"/agents/runs/{run.id}",
                }
            )
        if include_nodes and run:
            with db_session() as session:
                nodes = list(
                    session.scalars(
                        select(PaperChatWorkflowNodeRunRecord)
                        .where(PaperChatWorkflowNodeRunRecord.workflow_run_id == run.id)
                        .order_by(PaperChatWorkflowNodeRunRecord.sort_order)
                    )
                )
            payload["nodes"] = [
                {
                    "id": node.id,
                    "node_id": node.node_id,
                    "parent_node_id": node.parent_node_id,
                    "title": node.title,
                    "status": node.status,
                    "detail": node.detail,
                    "progress": node.progress,
                    "error_text": node.error_text,
                    "sort_order": node.sort_order,
                    "started_at": _dt(node.started_at),
                    "completed_at": _dt(node.completed_at),
                }
                for node in nodes
            ]
        elif include_nodes:
            payload["nodes"] = []
        if include_artifacts:
            artifacts = agent_repository.list_artifacts(task_id=task.id)
            payload["artifacts"] = [
                {
                    "id": artifact.id,
                    "task_id": artifact.task_id,
                    "workflow_run_id": artifact.workflow_run_id,
                    "artifact_type": artifact.artifact_type,
                    "title": artifact.title,
                    "content": artifact.content_text,
                    "uri": (artifact.metadata_json or {}).get("uri", ""),
                    "metadata": artifact.metadata_json or {},
                    "created_at": _dt(artifact.created_at),
                }
                for artifact in artifacts
            ]
        if include_run and run:
            payload["workflow_run"] = {
                "id": run.id,
                "task_id": run.task_id,
                "workflow_id": run.workflow_id,
                "conversation_id": run.conversation_id,
                "status": run.status,
                "current_node": run.current_node,
                "input": run.input_json or {},
                "output": run.output_json or {},
                "error": run.error_json or {},
                "started_at": _dt(run.started_at),
                "completed_at": _dt(run.completed_at),
                "created_at": _dt(run.created_at),
                "updated_at": _dt(run.updated_at),
            }
        elif include_run:
            payload["workflow_run"] = None
        return payload


task_service = TaskService()
