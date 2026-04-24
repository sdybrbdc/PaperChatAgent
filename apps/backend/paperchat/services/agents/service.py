from __future__ import annotations

import asyncio
import re
from typing import Any

from paperchat.api.errcode import AppError
from paperchat.agents.research_orchestrator.definition import BUILTIN_AGENT_WORKFLOWS, SMART_RESEARCH_ASSISTANT_SLUG
from paperchat.settings import get_settings
from paperchat.services.agent_repository import agent_repository
from paperchat.workflows.research_orchestrator import get_research_orchestrator_runner

ENV_PLACEHOLDER_RE = re.compile(r"^\$\{?[A-Z0-9_]+\}?$")


class AgentService:
    def ensure_builtin_workflows(self) -> None:
        for workflow in BUILTIN_AGENT_WORKFLOWS:
            agent_repository.upsert_builtin_workflow(
                slug=workflow.slug,
                name=workflow.name,
                description=workflow.description,
                version=workflow.version,
                definition=workflow.definition,
            )

    def _require_workflow(self, workflow_id_or_slug: str):
        self.ensure_builtin_workflows()
        workflow = agent_repository.get_workflow(workflow_id_or_slug)
        if workflow is None:
            raise AppError(status_code=404, code="AGENT_WORKFLOW_NOT_FOUND", message="智能体不存在")
        return workflow

    def _resolve_runtime(self, workflow):
        runtime_name = str((workflow.definition_json or {}).get("runtime") or "")
        try:
            return get_research_orchestrator_runner(runtime_name)
        except ValueError as exc:
            raise AppError(status_code=500, code="AGENT_RUNTIME_NOT_FOUND", message=str(exc)) from exc

    def _find_node(self, workflow, node_id: str) -> dict[str, Any] | None:
        for node in workflow.definition_json.get("nodes", []) or []:
            if node.get("id") == node_id:
                return node
            for sub_node in node.get("sub_nodes", []) or []:
                if sub_node.get("id") == node_id:
                    merged = {
                        "type": "sub_node",
                        "model_slot": node.get("model_slot", "conversation_model"),
                        "fallback_executor_key": node.get("fallback_executor_key", ""),
                        "input_source": node.get("input_source", ""),
                        "output_target": node.get("output_target", ""),
                        "handoff_rule": node.get("handoff_rule", ""),
                        **sub_node,
                    }
                    return merged
        return None

    def _override_by_node_id(self, *, user_id: str, workflow_id: str) -> dict[str, Any]:
        return {override.node_id: override for override in agent_repository.list_config_overrides(user_id=user_id, workflow_id=workflow_id)}

    def _node_payload(
        self,
        node: dict[str, Any],
        override=None,
        *,
        parent_node_id: str = "",
        overrides: dict[str, Any] | None = None,
        inherited: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload_source = {**(inherited or {}), **node}
        executor_key = override.executor_key if override and override.executor_key else payload_source.get("executor_key", "")
        fallback_executor_key = (
            override.fallback_executor_key
            if override and override.fallback_executor_key
            else payload_source.get("fallback_executor_key", "")
        )
        model_slot = override.model_slot if override and override.model_slot else payload_source.get("model_slot", "conversation_model")
        return {
            "id": payload_source.get("id", ""),
            "parent_node_id": parent_node_id,
            "title": payload_source.get("title", ""),
            "type": payload_source.get("type", "workflow_node"),
            "executor_key": executor_key,
            "fallback_executor_key": fallback_executor_key,
            "model_slot": model_slot,
            "current_model_name": self._resolve_model_name(model_slot),
            "input_source": payload_source.get("input_source", ""),
            "output_target": payload_source.get("output_target", ""),
            "description": payload_source.get("description", ""),
            "handoff_rule": payload_source.get("handoff_rule", ""),
            "config": override.config_json if override else {},
            "sub_nodes": [
                self._node_payload(
                    sub_node,
                    (overrides or {}).get(str(sub_node.get("id", ""))),
                    parent_node_id=str(payload_source.get("id", "")),
                    overrides=overrides,
                    inherited={
                        "type": "sub_node",
                        "model_slot": model_slot,
                        "fallback_executor_key": fallback_executor_key,
                        "input_source": payload_source.get("input_source", ""),
                        "output_target": payload_source.get("output_target", ""),
                        "handoff_rule": payload_source.get("handoff_rule", ""),
                    },
                )
                for sub_node in payload_source.get("sub_nodes", []) or []
            ],
        }

    def _resolve_model_name(self, model_slot: str) -> str:
        config = getattr(get_settings().multi_models, model_slot, None)
        if config is None:
            return ""
        model_name = str(getattr(config, "model_name", "") or "").strip()
        if not model_name or ENV_PLACEHOLDER_RE.fullmatch(model_name):
            return ""
        return model_name

    def _workflow_payload(self, workflow, *, user_id: str | None = None, include_definition: bool = False) -> dict[str, Any]:
        definition = workflow.definition_json or {}
        nodes = definition.get("nodes", []) or []
        payload = {
            "id": workflow.id,
            "slug": workflow.slug,
            "name": workflow.name,
            "description": workflow.description,
            "source_type": workflow.source_type,
            "status": workflow.status,
            "version": workflow.version,
            "node_count": len(nodes),
            "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
            "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
        }
        if include_definition:
            payload["definition"] = definition
            if user_id:
                payload["nodes"] = self._nodes_payload(workflow, user_id=user_id)
        return payload

    def _nodes_payload(self, workflow, *, user_id: str) -> list[dict[str, Any]]:
        overrides = self._override_by_node_id(user_id=user_id, workflow_id=workflow.id)
        return [
            self._node_payload(node, overrides.get(str(node.get("id", ""))), overrides=overrides)
            for node in workflow.definition_json.get("nodes", []) or []
        ]

    def _node_run_payload(self, node_run) -> dict[str, Any]:
        return {
            "id": node_run.id,
            "workflow_run_id": node_run.workflow_run_id,
            "node_id": node_run.node_id,
            "parent_node_id": node_run.parent_node_id,
            "title": node_run.title,
            "status": node_run.status,
            "detail": node_run.detail,
            "progress": node_run.progress,
            "input": node_run.input_json or {},
            "output": node_run.output_json or {},
            "metadata": node_run.metadata_json or {},
            "error_text": node_run.error_text,
            "sort_order": node_run.sort_order,
            "started_at": node_run.started_at.isoformat() if node_run.started_at else None,
            "completed_at": node_run.completed_at.isoformat() if node_run.completed_at else None,
        }

    def _run_payload(self, run, *, include_nodes: bool = False, include_artifacts: bool = True) -> dict[str, Any]:
        task = agent_repository.get_task(run.task_id)
        workflow = agent_repository.get_workflow(run.workflow_id)
        artifacts = agent_repository.list_artifacts(workflow_run_id=run.id) if include_artifacts else []
        report = next((artifact for artifact in artifacts if artifact.artifact_type == "markdown_report"), None)
        payload = {
            "id": run.id,
            "task_id": run.task_id,
            "workflow_id": run.workflow_id,
            "workflow_name": workflow.name if workflow else "",
            "conversation_id": run.conversation_id,
            "title": task.title if task else "",
            "status": run.status,
            "current_node": run.current_node,
            "progress": task.progress if task else 0,
            "summary": task.summary if task else "",
            "failed_reason": task.failed_reason if task else "",
            "detail_url": f"/agents/runs/{run.id}",
            "input": run.input_json or {},
            "output": run.output_json or {},
            "error": run.error_json or {},
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "updated_at": run.updated_at.isoformat() if run.updated_at else None,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "report": {
                "id": report.id,
                "title": report.title,
                "content": report.content_text,
                "metadata": report.metadata_json or {},
                "created_at": report.created_at.isoformat() if report.created_at else None,
            }
            if report
            else None,
        }
        if include_nodes:
            payload["nodes"] = [self._node_run_payload(item) for item in agent_repository.list_node_runs(run.id)]
        return payload

    def list_workflows_payload(self, user_id: str) -> dict[str, Any]:
        self.ensure_builtin_workflows()
        return {
            "items": [self._workflow_payload(workflow, user_id=user_id) for workflow in agent_repository.list_workflows()]
        }

    def get_workflow_payload(self, *, user_id: str, workflow_id: str) -> dict[str, Any]:
        workflow = self._require_workflow(workflow_id)
        return self._workflow_payload(workflow, user_id=user_id, include_definition=True)

    def get_nodes_payload(self, *, user_id: str, workflow_id: str, run_id: str | None = None) -> dict[str, Any]:
        workflow = self._require_workflow(workflow_id)
        if run_id:
            run = self._require_run(user_id=user_id, run_id=run_id)
            return {"items": [self._node_run_payload(node) for node in agent_repository.list_node_runs(run.id)]}
        return {"items": self._nodes_payload(workflow, user_id=user_id)}

    def save_node_config_payload(
        self,
        *,
        user_id: str,
        workflow_id: str,
        node_id: str,
        executor_key: str,
        fallback_executor_key: str,
        model_slot: str,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        workflow = self._require_workflow(workflow_id)
        node = self._find_node(workflow, node_id)
        if node is None:
            raise AppError(status_code=404, code="AGENT_NODE_NOT_FOUND", message="智能体节点不存在")
        override = agent_repository.upsert_config_override(
            user_id=user_id,
            workflow_id=workflow.id,
            node_id=node_id,
            executor_key=executor_key or node.get("executor_key", ""),
            fallback_executor_key=fallback_executor_key or node.get("fallback_executor_key", ""),
            model_slot=model_slot or "conversation_model",
            config=config or {},
        )
        return self._node_payload(node, override)

    def _require_run(self, *, user_id: str, run_id: str):
        run = agent_repository.get_run(run_id)
        if run is None or run.user_id != user_id:
            raise AppError(status_code=404, code="AGENT_RUN_NOT_FOUND", message="智能体运行不存在")
        return run

    async def create_run_payload(
        self,
        *,
        user_id: str,
        workflow_id: str,
        topic: str,
        conversation_id: str | None = None,
        max_papers: int = 6,
        start_background: bool = True,
    ) -> dict[str, Any]:
        workflow = self._require_workflow(workflow_id)
        runtime = self._resolve_runtime(workflow) if start_background else None
        topic = topic.strip()
        if not topic:
            raise AppError(status_code=400, code="AGENT_RUN_TOPIC_REQUIRED", message="研究主题不能为空")
        title = f"{workflow.name}：{topic[:48]}"
        task, run = agent_repository.create_task_and_run(
            user_id=user_id,
            conversation_id=conversation_id,
            workflow_id=workflow.id,
            title=title,
            input_payload={
                "topic": topic,
                "request": topic,
                "max_papers": max(1, min(max_papers, 20)),
                "source": "chat_tool" if conversation_id else "agents_api",
            },
        )
        agent_repository.create_node_runs(workflow_run_id=run.id, nodes=workflow.definition_json.get("nodes", []) or [])
        if start_background and runtime is not None:
            asyncio.create_task(runtime(run_id=run.id))
        return self._run_payload(run, include_nodes=True, include_artifacts=False)

    async def create_smart_research_run_from_chat(
        self,
        *,
        user_id: str,
        conversation_id: str,
        topic: str,
        max_papers: int = 6,
    ) -> dict[str, Any]:
        workflow = self._require_workflow(SMART_RESEARCH_ASSISTANT_SLUG)
        return await self.create_run_payload(
            user_id=user_id,
            workflow_id=workflow.id,
            conversation_id=conversation_id,
            topic=topic,
            max_papers=max_papers,
        )

    def get_run_payload(self, *, user_id: str, run_id: str) -> dict[str, Any]:
        run = self._require_run(user_id=user_id, run_id=run_id)
        return self._run_payload(run, include_nodes=True)

    def get_run_nodes_payload(self, *, user_id: str, run_id: str) -> dict[str, Any]:
        run = self._require_run(user_id=user_id, run_id=run_id)
        return {"items": [self._node_run_payload(node) for node in agent_repository.list_node_runs(run.id)]}


agent_service = AgentService()
