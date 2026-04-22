from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from paperchat.api.errcode import AppError
from paperchat.database.dao import memory_store
from paperchat.services.task.event_bus import publish_task_event


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskService:
    async def create_task(self, *, user_id: str, title: str, workspace_name: str = "默认研究工作区") -> dict:
        workspace = memory_store.find_workspace_by_name(user_id=user_id, name=workspace_name)
        if workspace is None:
            workspace = memory_store.create_workspace(user_id=user_id, name=workspace_name)
        task = memory_store.create_task(user_id=user_id, workspace_id=workspace.id, title=title)
        asyncio.create_task(self._run_demo_task(task.id))
        return memory_store.as_task_payload(task)

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
        return memory_store.as_task_payload(task)

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

    async def _run_demo_task(self, task_id: str) -> None:
        task = memory_store.get_task(task_id)
        if task is None:
            return

        task = memory_store.update_task(task_id, status="queued", detail="任务已创建")
        await self._emit(task_id, "task.created", "任务已创建")

        nodes = [
            ("search_agent_node", 20.0, "正在收束检索条件"),
            ("reading_agent_node", 45.0, "正在解析论文与资料"),
            ("analyse_agent_node", 70.0, "正在聚类与分析"),
            ("writing_agent_node", 85.0, "正在组织写作内容"),
            ("report_agent_node", 100.0, "正在生成主题探索包"),
        ]

        memory_store.update_task(task_id, status="running")
        for node_name, progress, detail in nodes:
            memory_store.update_task(
                task_id,
                current_node=node_name,
                progress_percent=progress,
                detail=detail,
            )
            await self._emit(task_id, "task.node.started", f"{node_name} 已开始")
            await self._emit(task_id, "task.progress", detail)
            await asyncio.sleep(0.4)
            await self._emit(task_id, "task.node.completed", f"{node_name} 已完成")

        memory_store.update_task(task_id, status="completed", detail="任务已完成")
        await self._emit(task_id, "task.completed", "任务已完成")


task_service = TaskService()
