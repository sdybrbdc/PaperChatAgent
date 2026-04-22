from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from paperchat.api.errcode import AppError
from paperchat.database.dao import memory_store
from paperchat.services.task.event_bus import publish_task_event
from paperchat.workflows import DEFAULT_WORKFLOW_ID, DEFAULT_WORKFLOW_NODES, run_research_workflow


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskService:
    async def create_task(
        self,
        *,
        user_id: str,
        title: str,
        workspace_name: str = "默认研究工作区",
        keywords: list[str] | None = None,
        source_config: dict | None = None,
    ) -> dict:
        workspace = memory_store.find_workspace_by_name(user_id=user_id, name=workspace_name)
        if workspace is None:
            workspace = memory_store.create_workspace(user_id=user_id, name=workspace_name)
        task = memory_store.create_task(user_id=user_id, workspace_id=workspace.id, title=title)
        memory_store.init_task_workflow(
            task_id=task.id,
            workflow_id=DEFAULT_WORKFLOW_ID,
            nodes=DEFAULT_WORKFLOW_NODES,
        )
        task = memory_store.update_task(task.id, detail="任务已创建")
        await self._emit(task.id, "task.created", "任务已创建")
        asyncio.create_task(
            self._run_workflow(
                task_id=task.id,
                user_id=user_id,
                workspace_id=workspace.id,
                topic=title,
                keywords=keywords or [],
                source_config=source_config or {},
            )
        )
        return self.get_task(user_id, task.id)

    async def retry_task(self, *, user_id: str, task_id: str) -> dict:
        task = memory_store.get_task(task_id)
        if task is None or task.user_id != user_id:
            raise AppError(status_code=404, code="TASK_NOT_FOUND", message="任务不存在")
        workspace = memory_store.get_workspace(task.workspace_id)
        workspace_name = workspace.name if workspace else "默认研究工作区"
        return await self.create_task(user_id=user_id, title=f"{task.title}（重试）", workspace_name=workspace_name)

    def get_task_report(self, *, user_id: str, task_id: str) -> dict:
        task = memory_store.get_task(task_id)
        if task is None or task.user_id != user_id:
            raise AppError(status_code=404, code="TASK_NOT_FOUND", message="任务不存在")
        artifact = memory_store.get_task_report(task_id)
        if artifact:
            return artifact
        return {
            "task_id": task.id,
            "status": task.status,
            "title": task.title,
            "summary": "这是当前任务的占位报告，用于前后端联调与 Swagger 展示。",
            "artifact_type": "markdown",
            "content_markdown": f"# {task.title}\n\n当前状态：{task.status}\n\n详细说明：{task.detail or '暂无'}",
        }

    def list_tasks(self, user_id: str) -> dict:
        items = [memory_store.as_task_payload(task) for task in memory_store.list_tasks(user_id)]
        return {
            "items": items,
            "page": 1,
            "page_size": len(items) or 20,
            "total": len(items),
            "has_more": False,
        }

    def get_task(self, user_id: str, task_id: str) -> dict:
        task = memory_store.get_task(task_id)
        if task is None or task.user_id != user_id:
            raise AppError(status_code=404, code="TASK_NOT_FOUND", message="任务不存在")
        payload = memory_store.as_task_payload(task)
        payload["workflow_id"] = DEFAULT_WORKFLOW_ID
        payload["nodes"] = memory_store.list_task_node_runs(task_id)
        return payload

    async def _emit(self, task_id: str, event_name: str, detail: str) -> None:
        task = memory_store.get_task(task_id)
        if task is None:
            return
        event = {
            "event": event_name,
            "data": {
                "task_id": task.id,
                "status": task.status,
                "current_node": task.current_node,
                "progress_percent": task.progress_percent,
                "detail": detail,
                "occurred_at": now_iso(),
            },
        }
        await memory_store.publish_task_event(task_id, event)
        try:
            await publish_task_event(task_id, event)
        except Exception:
            # Redis is used as the primary cross-process bus, but we keep local subscribers as fallback.
            pass

    async def _run_workflow(
        self,
        *,
        task_id: str,
        user_id: str,
        workspace_id: str,
        topic: str,
        keywords: list[str],
        source_config: dict,
    ) -> None:
        try:
            await run_research_workflow(
                task_service=self,
                task_id=task_id,
                user_id=user_id,
                workspace_id=workspace_id,
                topic=topic,
                keywords=keywords,
                source_config=source_config,
            )
        except Exception:
            return

    def _node_progress(self, node_id: str) -> float:
        for node in DEFAULT_WORKFLOW_NODES:
            if node.id == node_id:
                return node.progress_percent
        return 0.0

    async def mark_workflow_started(self, task_id: str) -> None:
        memory_store.update_task(task_id, status="running", detail="工作流已启动")
        await self._emit(task_id, "task.progress", "工作流已启动")

    async def mark_node_started(self, *, task_id: str, node_id: str, detail: str) -> None:
        memory_store.update_task_node_run(task_id, node_id, status="running", detail=detail)
        memory_store.update_task(
            task_id,
            status="running",
            current_node=node_id,
            progress_percent=self._node_progress(node_id),
            detail=detail,
        )
        await self._emit(task_id, "task.node.started", detail)
        await self._emit(task_id, "task.progress", detail)

    async def mark_node_progress(self, *, task_id: str, node_id: str, detail: str) -> None:
        memory_store.update_task_node_run(task_id, node_id, status="running", detail=detail)
        memory_store.update_task(
            task_id,
            status="running",
            current_node=node_id,
            progress_percent=self._node_progress(node_id),
            detail=detail,
        )
        await self._emit(task_id, "task.progress", detail)

    async def mark_node_completed(self, *, task_id: str, node_id: str, detail: str) -> None:
        memory_store.update_task_node_run(task_id, node_id, status="completed", detail=detail)
        memory_store.update_task(
            task_id,
            status="running",
            current_node=node_id,
            progress_percent=self._node_progress(node_id),
            detail=detail,
        )
        await self._emit(task_id, "task.node.completed", detail)

    async def save_report(self, *, task_id: str, title: str, content_markdown: str, summary: str) -> None:
        memory_store.save_task_report(
            task_id,
            title=title,
            content_markdown=content_markdown,
            summary=summary,
        )

    async def mark_task_completed(self, *, task_id: str, detail: str) -> None:
        task = memory_store.update_task(task_id, status="completed", progress_percent=100.0, detail=detail)
        artifact = memory_store.get_task_report(task_id)
        if artifact and task is not None:
            artifact["status"] = task.status
        await self._emit(task_id, "task.completed", detail)

    async def mark_task_failed(self, *, task_id: str, node_id: str | None, detail: str) -> None:
        task = memory_store.get_task(task_id)
        if task is None:
            return
        memory_store.update_task(task_id, status="failed", current_node=node_id or task.current_node, detail=detail)
        if node_id:
            memory_store.update_task_node_run(task_id, node_id, status="failed", detail=detail)
            await self._emit(task_id, "task.node.failed", detail)
        await self._emit(task_id, "task.failed", detail)


task_service = TaskService()
