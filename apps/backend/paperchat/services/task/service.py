from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone

from paperchat.api.errcode import AppError
from paperchat.database.dao import memory_store
from paperchat.workflows import DEFAULT_WORKFLOW_ID, DEFAULT_WORKFLOW_NODES, run_research_workflow


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


INTERNAL_TASK_CONTAINER_NAME = "__paperchat_tasks__"
DEFAULT_NODE_FALLBACK_OVERRIDES = {
    "search_agent_node": [{"reasoning_model": "conversation_model"}],
    "analyse_agent_node": [{"reasoning_model": "conversation_model"}],
    "writing_agent_node": [{"reasoning_model": "conversation_model"}],
    "report_agent_node": [{"reasoning_model": "conversation_model"}],
}


class TaskService:
    def __init__(self) -> None:
        self.active_runtimes: dict[str, asyncio.Task] = {}

    def _build_recovery_policy(self, source_config: dict | None = None) -> dict:
        source_config = source_config or {}
        configured = deepcopy(source_config.get("task_recovery_policy", {}))
        fallback_overrides = deepcopy(DEFAULT_NODE_FALLBACK_OVERRIDES)
        fallback_overrides.update(configured.get("fallback_model_overrides", {}))
        return {
            "runtime": "in_process_asyncio",
            "max_retries_per_node": int(configured.get("max_retries_per_node", 2)),
            "fallback_model_overrides": fallback_overrides,
        }

    def _build_initial_workflow_state(
        self,
        *,
        task_id: str,
        user_id: str,
        workspace_id: str,
        topic: str,
        keywords: list[str],
        source_config: dict,
    ) -> dict:
        return {
            "task_id": task_id,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "topic": topic,
            "keywords": keywords,
            "source_config": source_config,
            "search_queries": [],
            "papers": [],
            "reading_notes": [],
            "analysis_clusters": [],
            "deep_analysis_results": [],
            "analysis_markdown": "",
            "writing_outline": [],
            "writing_sections": [],
            "report_markdown": "",
            "report_summary": "",
            "last_detail": "",
            "failed_node": None,
            "error": None,
        }

    def _start_runtime(
        self,
        *,
        task_id: str,
        user_id: str,
        workspace_id: str,
        topic: str,
        keywords: list[str],
        source_config: dict,
        resume_from_node: str | None = None,
    ) -> None:
        runtime = asyncio.create_task(
            self._run_workflow(
                task_id=task_id,
                user_id=user_id,
                workspace_id=workspace_id,
                topic=topic,
                keywords=keywords,
                source_config=source_config,
                resume_from_node=resume_from_node,
            )
        )
        self.active_runtimes[task_id] = runtime
        runtime.add_done_callback(lambda _: self.active_runtimes.pop(task_id, None))

    async def create_task(
        self,
        *,
        user_id: str,
        title: str,
        source_session_id: str | None = None,
        keywords: list[str] | None = None,
        source_config: dict | None = None,
    ) -> dict:
        keywords = keywords or []
        source_config = source_config or {}
        workspace = memory_store.find_workspace_by_name(user_id=user_id, name=INTERNAL_TASK_CONTAINER_NAME)
        if workspace is None:
            workspace = memory_store.create_workspace(user_id=user_id, name=INTERNAL_TASK_CONTAINER_NAME)

        task = memory_store.create_task(
            user_id=user_id,
            workspace_id=workspace.id,
            title=title,
            payload_json={
                "topic": title,
                "keywords": keywords,
                "source_config": source_config,
                "source_session_id": source_session_id,
            },
        )
        initial_state = self._build_initial_workflow_state(
            task_id=task.id,
            user_id=user_id,
            workspace_id=workspace.id,
            topic=title,
            keywords=keywords,
            source_config=source_config,
        )
        memory_store.init_task_workflow(
            task_id=task.id,
            workflow_id=DEFAULT_WORKFLOW_ID,
            nodes=DEFAULT_WORKFLOW_NODES,
            workflow_state=initial_state,
            recovery_policy=self._build_recovery_policy(source_config),
        )
        memory_store.update_task(task.id, detail="任务已创建，准备在当前进程内执行")
        await self._emit(task.id, "task.created", "任务已创建，准备在当前进程内执行")
        self._start_runtime(
            task_id=task.id,
            user_id=user_id,
            workspace_id=workspace.id,
            topic=title,
            keywords=keywords,
            source_config=source_config,
        )
        return self.get_task(user_id, task.id)

    async def retry_task(self, *, user_id: str, task_id: str) -> dict:
        task = memory_store.get_task(task_id)
        if task is None or task.user_id != user_id:
            raise AppError(status_code=404, code="TASK_NOT_FOUND", message="任务不存在")
        payload = dict(task.payload_json or {})
        return await self.create_task(
            user_id=user_id,
            title=f"{task.title}（重试）",
            source_session_id=payload.get("source_session_id"),
            keywords=list(payload.get("keywords", [])),
            source_config=dict(payload.get("source_config", {})),
        )

    async def resume_task(
        self,
        *,
        user_id: str,
        task_id: str,
        resume_from_node: str | None = None,
        model_slot_overrides: dict[str, str] | None = None,
    ) -> dict:
        task = memory_store.get_task(task_id)
        if task is None or task.user_id != user_id:
            raise AppError(status_code=404, code="TASK_NOT_FOUND", message="任务不存在")
        if task.status not in {"paused", "failed"}:
            raise AppError(status_code=409, code="TASK_NOT_RESUMABLE", message="当前任务不处于可恢复状态")
        if task_id in self.active_runtimes:
            raise AppError(status_code=409, code="TASK_ALREADY_RUNNING", message="当前任务正在执行中")

        checkpoint = memory_store.get_task_checkpoint(task_id)
        target_node = resume_from_node or checkpoint.get("resume_from_node") or task.current_node
        if not target_node:
            raise AppError(status_code=400, code="TASK_RESUME_NODE_MISSING", message="缺少可恢复的节点信息")

        resumed = memory_store.prepare_task_resume(
            task_id,
            resume_from_node=target_node,
            model_slot_overrides=model_slot_overrides or {},
        )
        if resumed is None:
            raise AppError(status_code=400, code="TASK_RESUME_NODE_INVALID", message="指定的恢复节点不存在")

        memory_store.update_task(
            task_id,
            status="queued",
            current_node=target_node,
            detail=f"准备从 {target_node} 继续执行",
        )
        await self._emit(task_id, "task.resumed", f"准备从 {target_node} 继续执行")

        payload = dict(task.payload_json or {})
        self._start_runtime(
            task_id=task.id,
            user_id=user_id,
            workspace_id=task.workspace_id,
            topic=str(payload.get("topic", task.title)),
            keywords=list(payload.get("keywords", [])),
            source_config=dict(payload.get("source_config", {})),
            resume_from_node=target_node,
        )
        return self.get_task(user_id, task.id)

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

    async def _run_workflow(
        self,
        *,
        task_id: str,
        user_id: str,
        workspace_id: str,
        topic: str,
        keywords: list[str],
        source_config: dict,
        resume_from_node: str | None = None,
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
                resume_from_node=resume_from_node,
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

    async def mark_node_retrying(self, *, task_id: str, node_id: str, detail: str) -> None:
        memory_store.update_task_node_run(task_id, node_id, status="retrying", detail=detail)
        memory_store.update_task(
            task_id,
            status="running",
            current_node=node_id,
            progress_percent=self._node_progress(node_id),
            detail=detail,
        )
        await self._emit(task_id, "task.node.retrying", detail)
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

    async def mark_task_paused(self, *, task_id: str, node_id: str, detail: str) -> None:
        memory_store.update_task(task_id, status="paused", current_node=node_id, detail=detail)
        memory_store.update_task_node_run(task_id, node_id, status="paused", detail=detail)
        await self._emit(task_id, "task.node.paused", detail)
        await self._emit(task_id, "task.paused", detail)

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
