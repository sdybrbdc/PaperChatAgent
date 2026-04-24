from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import asc, select

from paperchat.database.models.tables import (
    PaperChatAgentNodeConfigOverrideRecord,
    PaperChatAgentWorkflowRecord,
    PaperChatResearchTaskRecord,
    PaperChatTaskArtifactRecord,
    PaperChatWorkflowNodeRunRecord,
    PaperChatWorkflowRunRecord,
)
from paperchat.database.sql import db_session


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentRepository:
    def upsert_builtin_workflow(
        self,
        *,
        slug: str,
        name: str,
        description: str,
        version: str,
        definition: dict[str, Any],
    ):
        with db_session() as session:
            workflow = session.scalar(select(PaperChatAgentWorkflowRecord).where(PaperChatAgentWorkflowRecord.slug == slug))
            if workflow is None:
                workflow = PaperChatAgentWorkflowRecord(
                    slug=slug,
                    name=name,
                    description=description,
                    source_type="builtin",
                    status="active",
                    version=version,
                    definition_json=definition,
                )
                session.add(workflow)
            else:
                workflow.name = name
                workflow.description = description
                workflow.source_type = "builtin"
                workflow.status = "active"
                workflow.version = version
                workflow.definition_json = definition
                workflow.updated_at = utcnow()
            session.flush()
            return workflow

    def list_workflows(self):
        with db_session() as session:
            return list(
                session.scalars(
                    select(PaperChatAgentWorkflowRecord)
                    .where(PaperChatAgentWorkflowRecord.status != "deleted")
                    .order_by(asc(PaperChatAgentWorkflowRecord.created_at))
                )
            )

    def get_workflow(self, workflow_id_or_slug: str):
        with db_session() as session:
            return session.scalar(
                select(PaperChatAgentWorkflowRecord).where(
                    (PaperChatAgentWorkflowRecord.id == workflow_id_or_slug)
                    | (PaperChatAgentWorkflowRecord.slug == workflow_id_or_slug)
                )
            )

    def list_config_overrides(self, *, user_id: str, workflow_id: str):
        with db_session() as session:
            return list(
                session.scalars(
                    select(PaperChatAgentNodeConfigOverrideRecord)
                    .where(
                        PaperChatAgentNodeConfigOverrideRecord.user_id == user_id,
                        PaperChatAgentNodeConfigOverrideRecord.workflow_id == workflow_id,
                    )
                    .order_by(asc(PaperChatAgentNodeConfigOverrideRecord.node_id))
                )
            )

    def get_config_override(self, *, user_id: str, workflow_id: str, node_id: str):
        with db_session() as session:
            return session.scalar(
                select(PaperChatAgentNodeConfigOverrideRecord).where(
                    PaperChatAgentNodeConfigOverrideRecord.user_id == user_id,
                    PaperChatAgentNodeConfigOverrideRecord.workflow_id == workflow_id,
                    PaperChatAgentNodeConfigOverrideRecord.node_id == node_id,
                )
            )

    def upsert_config_override(
        self,
        *,
        user_id: str,
        workflow_id: str,
        node_id: str,
        executor_key: str,
        fallback_executor_key: str,
        model_slot: str,
        config: dict[str, Any],
    ):
        with db_session() as session:
            override = session.scalar(
                select(PaperChatAgentNodeConfigOverrideRecord).where(
                    PaperChatAgentNodeConfigOverrideRecord.user_id == user_id,
                    PaperChatAgentNodeConfigOverrideRecord.workflow_id == workflow_id,
                    PaperChatAgentNodeConfigOverrideRecord.node_id == node_id,
                )
            )
            if override is None:
                override = PaperChatAgentNodeConfigOverrideRecord(
                    user_id=user_id,
                    workflow_id=workflow_id,
                    node_id=node_id,
                )
                session.add(override)
            override.executor_key = executor_key
            override.fallback_executor_key = fallback_executor_key
            override.model_slot = model_slot or "conversation_model"
            override.config_json = config
            override.updated_at = utcnow()
            session.flush()
            return override

    def create_task_and_run(
        self,
        *,
        user_id: str,
        conversation_id: str | None,
        workflow_id: str,
        title: str,
        input_payload: dict[str, Any],
    ) -> tuple[PaperChatResearchTaskRecord, PaperChatWorkflowRunRecord]:
        with db_session() as session:
            task = PaperChatResearchTaskRecord(
                user_id=user_id,
                conversation_id=conversation_id,
                workflow_id=workflow_id,
                title=title,
                status="pending",
                progress=0,
            )
            session.add(task)
            session.flush()
            run = PaperChatWorkflowRunRecord(
                task_id=task.id,
                user_id=user_id,
                conversation_id=conversation_id,
                workflow_id=workflow_id,
                status="pending",
                input_json=input_payload,
            )
            session.add(run)
            session.flush()
            return task, run

    def create_node_runs(self, *, workflow_run_id: str, nodes: list[dict[str, Any]]):
        with db_session() as session:
            records: list[PaperChatWorkflowNodeRunRecord] = []
            sort_order = 0
            for node in nodes:
                sort_order += 1
                record = PaperChatWorkflowNodeRunRecord(
                    workflow_run_id=workflow_run_id,
                    node_id=node["id"],
                    parent_node_id="",
                    title=node["title"],
                    metadata_json={
                        "type": node.get("type", "workflow_node"),
                        "executor_key": node.get("executor_key", ""),
                        "model_slot": node.get("model_slot", "conversation_model"),
                        "description": node.get("description", ""),
                    },
                    sort_order=sort_order,
                )
                session.add(record)
                records.append(record)
                for sub_node in node.get("sub_nodes", []) or []:
                    sort_order += 1
                    sub_record = PaperChatWorkflowNodeRunRecord(
                        workflow_run_id=workflow_run_id,
                        node_id=sub_node["id"],
                        parent_node_id=node["id"],
                        title=sub_node["title"],
                        metadata_json={
                            "type": "sub_node",
                            "executor_key": sub_node.get("executor_key", ""),
                            "description": sub_node.get("description", ""),
                        },
                        sort_order=sort_order,
                    )
                    session.add(sub_record)
                    records.append(sub_record)
            session.flush()
            return records

    def update_task(self, task_id: str, **changes):
        with db_session() as session:
            task = session.get(PaperChatResearchTaskRecord, task_id)
            if task is None:
                return None
            for key, value in changes.items():
                setattr(task, key, value)
            task.updated_at = utcnow()
            session.flush()
            return task

    def update_run(self, run_id: str, **changes):
        with db_session() as session:
            run = session.get(PaperChatWorkflowRunRecord, run_id)
            if run is None:
                return None
            for key, value in changes.items():
                setattr(run, key, value)
            run.updated_at = utcnow()
            session.flush()
            return run

    def update_node_run(self, *, workflow_run_id: str, node_id: str, **changes):
        with db_session() as session:
            node = session.scalar(
                select(PaperChatWorkflowNodeRunRecord).where(
                    PaperChatWorkflowNodeRunRecord.workflow_run_id == workflow_run_id,
                    PaperChatWorkflowNodeRunRecord.node_id == node_id,
                )
            )
            if node is None:
                return None
            for key, value in changes.items():
                setattr(node, key, value)
            session.flush()
            return node

    def get_run(self, run_id: str):
        with db_session() as session:
            return session.get(PaperChatWorkflowRunRecord, run_id)

    def get_task(self, task_id: str):
        with db_session() as session:
            return session.get(PaperChatResearchTaskRecord, task_id)

    def list_node_runs(self, run_id: str):
        with db_session() as session:
            return list(
                session.scalars(
                    select(PaperChatWorkflowNodeRunRecord)
                    .where(PaperChatWorkflowNodeRunRecord.workflow_run_id == run_id)
                    .order_by(asc(PaperChatWorkflowNodeRunRecord.sort_order))
                )
            )

    def create_artifact(
        self,
        *,
        task_id: str,
        workflow_run_id: str,
        artifact_type: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ):
        with db_session() as session:
            artifact = PaperChatTaskArtifactRecord(
                task_id=task_id,
                workflow_run_id=workflow_run_id,
                artifact_type=artifact_type,
                title=title,
                content_text=content,
                metadata_json=metadata or {},
            )
            session.add(artifact)
            session.flush()
            return artifact

    def list_artifacts(self, *, task_id: str | None = None, workflow_run_id: str | None = None):
        with db_session() as session:
            statement = select(PaperChatTaskArtifactRecord).order_by(asc(PaperChatTaskArtifactRecord.created_at))
            if task_id:
                statement = statement.where(PaperChatTaskArtifactRecord.task_id == task_id)
            if workflow_run_id:
                statement = statement.where(PaperChatTaskArtifactRecord.workflow_run_id == workflow_run_id)
            return list(session.scalars(statement))


agent_repository = AgentRepository()
