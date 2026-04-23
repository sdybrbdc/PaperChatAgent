from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import desc, select

from paperchat.database.models.tables import (
    PaperChatInboxConversationRecord,
    PaperChatKnowledgeFileRecord,
    PaperChatMessageRecord,
    PaperChatResearchTaskRecord,
    PaperChatSessionRecord,
    PaperChatUserRecord,
    PaperChatUserSessionRecord,
    PaperChatWorkspaceRecord,
)
from paperchat.database.sql import db_session


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_value(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


class SQLBackedStore:
    def __init__(self) -> None:
        self.task_events: dict[str, list[dict]] = {}
        self.task_subscribers: dict[str, set[asyncio.Queue]] = {}
        self.task_node_runs: dict[str, dict[str, dict]] = {}
        self.task_reports: dict[str, dict] = {}

    def create_user(self, *, email: str, password_hash: str, display_name: str):
        with db_session() as session:
            user = PaperChatUserRecord(email=email, password_hash=password_hash, display_name=display_name)
            session.add(user)
            session.flush()
            return user

    def get_user(self, user_id: str):
        with db_session() as session:
            return session.get(PaperChatUserRecord, user_id)

    def get_user_by_email(self, email: str):
        with db_session() as session:
            return session.scalar(select(PaperChatUserRecord).where(PaperChatUserRecord.email == email))

    def create_default_inbox(self, user_id: str):
        with db_session() as session:
            inbox = PaperChatInboxConversationRecord(user_id=user_id)
            session.add(inbox)
            session.flush()

            chat_session = PaperChatSessionRecord(
                user_id=user_id,
                title="新聊天",
                scope="inbox",
                inbox_conversation_id=inbox.id,
            )
            session.add(chat_session)
            session.flush()
            return inbox, chat_session

    def get_inbox_by_user(self, user_id: str):
        with db_session() as session:
            return session.scalar(
                select(PaperChatInboxConversationRecord).where(PaperChatInboxConversationRecord.user_id == user_id)
            )

    def get_or_create_default_session(self, user_id: str):
        inbox = self.get_inbox_by_user(user_id)
        if inbox is None:
            return self.create_default_inbox(user_id)

        with db_session() as session:
            current_session = session.scalar(
                select(PaperChatSessionRecord)
                .where(
                    PaperChatSessionRecord.user_id == user_id,
                    PaperChatSessionRecord.scope == "inbox",
                    PaperChatSessionRecord.inbox_conversation_id == inbox.id,
                )
                .order_by(desc(PaperChatSessionRecord.updated_at))
            )
            if current_session is not None:
                return inbox, current_session

        return self.create_default_inbox(user_id)

    def get_chat_session(self, session_id: str):
        with db_session() as session:
            return session.get(PaperChatSessionRecord, session_id)

    def create_conversation(self, *, user_id: str, title: str = "新聊天"):
        inbox = self.get_inbox_by_user(user_id)
        if inbox is None:
            inbox, _ = self.create_default_inbox(user_id)

        with db_session() as session:
            chat_session = PaperChatSessionRecord(
                user_id=user_id,
                title=title,
                scope="inbox",
                inbox_conversation_id=inbox.id,
            )
            session.add(chat_session)
            session.flush()
            return chat_session

    def update_chat_session(self, session_id: str, **changes):
        with db_session() as session:
            chat_session = session.get(PaperChatSessionRecord, session_id)
            if chat_session is None:
                return None
            for key, value in changes.items():
                setattr(chat_session, key, value)
            chat_session.updated_at = utcnow()
            session.flush()
            return chat_session

    def list_conversations(self, user_id: str):
        with db_session() as session:
            return list(
                session.scalars(
                    select(PaperChatSessionRecord)
                    .where(PaperChatSessionRecord.user_id == user_id)
                    .order_by(desc(PaperChatSessionRecord.updated_at))
                )
            )

    def create_workspace(self, *, user_id: str, name: str, description: str = ""):
        with db_session() as session:
            workspace = PaperChatWorkspaceRecord(user_id=user_id, name=name, description=description)
            session.add(workspace)
            session.flush()
            return workspace

    def update_workspace(self, workspace_id: str, **changes):
        with db_session() as session:
            workspace = session.get(PaperChatWorkspaceRecord, workspace_id)
            if workspace is None:
                return None
            for key, value in changes.items():
                setattr(workspace, key, value)
            workspace.updated_at = utcnow()
            session.flush()
            return workspace

    def get_workspace(self, workspace_id: str):
        with db_session() as session:
            return session.get(PaperChatWorkspaceRecord, workspace_id)

    def find_workspace_by_name(self, *, user_id: str, name: str):
        with db_session() as session:
            return session.scalar(
                select(PaperChatWorkspaceRecord).where(
                    PaperChatWorkspaceRecord.user_id == user_id,
                    PaperChatWorkspaceRecord.name == name,
                )
            )

    def list_workspaces(self, user_id: str):
        with db_session() as session:
            return list(
                session.scalars(
                    select(PaperChatWorkspaceRecord)
                    .where(PaperChatWorkspaceRecord.user_id == user_id)
                    .order_by(desc(PaperChatWorkspaceRecord.updated_at))
                )
            )

    def add_message(
        self,
        *,
        session_id: str,
        user_id: str | None,
        role: str,
        message_type: str,
        content: str,
        metadata: dict | None = None,
        citations: list[dict] | None = None,
    ):
        with db_session() as session:
            message = PaperChatMessageRecord(
                session_id=session_id,
                user_id=user_id,
                role=role,
                message_type=message_type,
                content=content,
                metadata_json=metadata or {},
                citations_json=citations or [],
            )
            session.add(message)
            session.flush()

            chat_session = session.get(PaperChatSessionRecord, session_id)
            if chat_session is not None:
                chat_session.last_message_at = message.created_at
                chat_session.updated_at = message.created_at
                if chat_session.title in {"默认聊天页", "新聊天"}:
                    stripped_title = content.replace("\n", " ").strip()
                    if stripped_title:
                        chat_session.title = stripped_title[:24]
                if chat_session.inbox_conversation_id:
                    inbox = session.get(PaperChatInboxConversationRecord, chat_session.inbox_conversation_id)
                    if inbox is not None:
                        inbox.last_message_at = message.created_at
                        inbox.updated_at = message.created_at
            return message

    def list_messages(self, session_id: str):
        with db_session() as session:
            return list(
                session.scalars(
                    select(PaperChatMessageRecord)
                    .where(PaperChatMessageRecord.session_id == session_id)
                    .order_by(PaperChatMessageRecord.created_at.asc())
                )
            )

    def get_recent_context_messages(self, session_id: str, limit: int):
        messages = self.list_messages(session_id)
        return messages[-limit:]

    def get_messages_since(self, session_id: str, last_message_id: str | None):
        messages = self.list_messages(session_id)
        if not last_message_id:
            return messages
        try:
            index = next(i for i, message in enumerate(messages) if message.id == last_message_id)
        except StopIteration:
            return messages
        return messages[index + 1 :]

    def create_user_session(self, *, user_id: str, refresh_token: str, expires_at: datetime):
        with db_session() as session:
            record = PaperChatUserSessionRecord(
                user_id=user_id,
                refresh_token_hash=hash_value(refresh_token),
                expires_at=expires_at,
            )
            session.add(record)
            session.flush()
            return record

    def get_user_session(self, session_id: str):
        with db_session() as session:
            return session.get(PaperChatUserSessionRecord, session_id)

    def update_refresh_token(self, session_id: str, refresh_token: str, expires_at: datetime) -> None:
        with db_session() as session:
            record = session.get(PaperChatUserSessionRecord, session_id)
            if record is None:
                return
            record.refresh_token_hash = hash_value(refresh_token)
            record.expires_at = expires_at
            record.updated_at = utcnow()

    def revoke_user_session(self, session_id: str) -> None:
        with db_session() as session:
            record = session.get(PaperChatUserSessionRecord, session_id)
            if record is None:
                return
            record.revoked_at = utcnow()
            record.updated_at = utcnow()

    def create_task(
        self,
        *,
        user_id: str,
        workspace_id: str,
        title: str,
        payload_json: dict | None = None,
        checkpoint_json: dict | None = None,
    ):
        with db_session() as session:
            task = PaperChatResearchTaskRecord(
                user_id=user_id,
                workspace_id=workspace_id,
                title=title,
                payload_json=payload_json or {},
                checkpoint_json=checkpoint_json or {},
            )
            session.add(task)
            session.flush()
            self.task_events.setdefault(task.id, [])
            self.task_subscribers.setdefault(task.id, set())
            self.task_node_runs[task.id] = dict((task.checkpoint_json or {}).get("node_runs", {}))
            return task

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

    def get_task(self, task_id: str):
        with db_session() as session:
            return session.get(PaperChatResearchTaskRecord, task_id)

    def get_task_checkpoint(self, task_id: str) -> dict:
        task = self.get_task(task_id)
        if task is None:
            return {}
        checkpoint = task.checkpoint_json or {}
        return dict(checkpoint)

    def update_task_checkpoint(self, task_id: str, **changes) -> dict | None:
        with db_session() as session:
            task = session.get(PaperChatResearchTaskRecord, task_id)
            if task is None:
                return None
            checkpoint = dict(task.checkpoint_json or {})
            checkpoint.update(changes)
            task.checkpoint_json = checkpoint
            task.updated_at = utcnow()
            session.flush()
            if "node_runs" in checkpoint:
                self.task_node_runs[task_id] = {
                    node_id: dict(node_payload) for node_id, node_payload in checkpoint["node_runs"].items()
                }
            return checkpoint

    def list_tasks(self, user_id: str):
        with db_session() as session:
            return list(
                session.scalars(
                    select(PaperChatResearchTaskRecord)
                    .where(PaperChatResearchTaskRecord.user_id == user_id)
                    .order_by(desc(PaperChatResearchTaskRecord.updated_at))
                )
            )

    def _ensure_task_runtime_loaded(self, task_id: str) -> None:
        if task_id in self.task_node_runs and self.task_node_runs[task_id]:
            return
        checkpoint = self.get_task_checkpoint(task_id)
        node_runs = checkpoint.get("node_runs", {})
        self.task_node_runs[task_id] = {
            node_id: dict(node_payload) for node_id, node_payload in node_runs.items()
        }

    def init_task_workflow(
        self,
        *,
        task_id: str,
        workflow_id: str,
        nodes: Sequence,
        workflow_state: dict | None = None,
        recovery_policy: dict | None = None,
    ) -> None:
        self.task_node_runs[task_id] = {
            node.id: {
                **node.as_payload(status="queued", detail="等待执行"),
                "workflow_id": workflow_id,
                "attempt_count": 0,
                "last_error_code": "",
                "last_error_message": "",
                "input_snapshot_json": {},
                "output_snapshot_json": {},
                "checkpoint_json": {},
                "active_model_overrides": {},
            }
            for node in nodes
        }
        self.update_task_checkpoint(
            task_id,
            workflow_id=workflow_id,
            workflow_state=workflow_state or {},
            node_runs=self.task_node_runs[task_id],
            resume_from_node=None,
            failure_context={},
            recovery_policy=recovery_policy or {},
            active_model_overrides={},
        )

    def list_task_node_runs(self, task_id: str) -> list[dict]:
        self._ensure_task_runtime_loaded(task_id)
        node_runs = list(self.task_node_runs.get(task_id, {}).values())
        return sorted(node_runs, key=lambda item: item.get("order", 0))

    def update_task_node_run(self, task_id: str, node_id: str, **changes) -> dict | None:
        self._ensure_task_runtime_loaded(task_id)
        node_runs = self.task_node_runs.setdefault(task_id, {})
        node = node_runs.get(node_id)
        if node is None:
            return None

        node.update(changes)
        now = utcnow().isoformat()
        status = str(node.get("status", ""))
        if status == "running" and not node.get("started_at"):
            node["started_at"] = now
        if status in {"completed", "failed", "canceled", "paused"}:
            node["completed_at"] = now
        self.update_task_checkpoint(task_id, node_runs=node_runs)
        return node

    def update_task_workflow_state(self, task_id: str, workflow_state: dict) -> dict | None:
        return self.update_task_checkpoint(task_id, workflow_state=workflow_state, resume_from_node=None, failure_context={})

    def record_task_failure_context(
        self,
        task_id: str,
        *,
        resume_from_node: str,
        failure_context: dict,
        active_model_overrides: dict | None = None,
    ) -> dict | None:
        return self.update_task_checkpoint(
            task_id,
            resume_from_node=resume_from_node,
            failure_context=failure_context,
            active_model_overrides=active_model_overrides or {},
        )

    def prepare_task_resume(
        self,
        task_id: str,
        *,
        resume_from_node: str,
        model_slot_overrides: dict[str, str] | None = None,
    ) -> dict | None:
        self._ensure_task_runtime_loaded(task_id)
        node_runs = self.task_node_runs.setdefault(task_id, {})
        current = node_runs.get(resume_from_node)
        if current is None:
            return None

        resume_order = int(current.get("order", 0))
        for node in node_runs.values():
            if int(node.get("order", 0)) < resume_order:
                continue
            node["status"] = "pending"
            node["detail"] = "等待继续执行"
            node["started_at"] = None
            node["completed_at"] = None
            node["last_error_code"] = ""
            node["last_error_message"] = ""
            node["output_snapshot_json"] = {}
            node["checkpoint_json"] = {}
            node["active_model_overrides"] = model_slot_overrides or {}
        return self.update_task_checkpoint(
            task_id,
            node_runs=node_runs,
            resume_from_node=resume_from_node,
            failure_context={},
            active_model_overrides=model_slot_overrides or {},
        )

    def save_task_report(
        self,
        task_id: str,
        *,
        title: str,
        content_markdown: str,
        summary: str,
        artifact_type: str = "markdown",
    ) -> dict:
        task = self.get_task(task_id)
        payload = {
            "task_id": task_id,
            "status": task.status if task else "completed",
            "title": title,
            "summary": summary,
            "artifact_type": artifact_type,
            "content_markdown": content_markdown,
            "updated_at": utcnow().isoformat(),
        }
        self.task_reports[task_id] = payload
        return payload

    def get_task_report(self, task_id: str) -> dict | None:
        return self.task_reports.get(task_id)

    def create_knowledge_file(
        self,
        *,
        user_id: str,
        source_type: str,
        title: str,
        source_url: str | None = None,
        object_key: str | None = None,
        parser_status: str = "uploaded",
        index_status: str = "pending",
        metadata_json: dict | None = None,
        workspace_id: str | None = None,
    ):
        with db_session() as session:
            record = PaperChatKnowledgeFileRecord(
                user_id=user_id,
                workspace_id=workspace_id,
                source_type=source_type,
                title=title,
                source_url=source_url,
                object_key=object_key,
                parser_status=parser_status,
                index_status=index_status,
                metadata_json=metadata_json or {},
            )
            session.add(record)
            session.flush()
            return record

    def list_knowledge_files(self, user_id: str):
        with db_session() as session:
            return list(
                session.scalars(
                    select(PaperChatKnowledgeFileRecord)
                    .where(PaperChatKnowledgeFileRecord.user_id == user_id)
                    .order_by(desc(PaperChatKnowledgeFileRecord.updated_at))
                )
            )

    async def publish_task_event(self, task_id: str, event: dict) -> None:
        self.task_events.setdefault(task_id, []).append(event)
        for queue in list(self.task_subscribers.get(task_id, set())):
            await queue.put(event)

    def subscribe_task_events(self, task_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self.task_subscribers.setdefault(task_id, set()).add(queue)
        return queue

    def unsubscribe_task_events(self, task_id: str, queue: asyncio.Queue) -> None:
        self.task_subscribers.setdefault(task_id, set()).discard(queue)

    def task_snapshot(self, task_id: str) -> dict | None:
        task = self.get_task(task_id)
        if not task:
            return None
        checkpoint = self.get_task_checkpoint(task_id)
        return {
            "task_id": task.id,
            "status": task.status,
            "current_node": task.current_node,
            "progress_percent": task.progress_percent,
            "detail": task.detail,
            "occurred_at": utcnow().isoformat(),
            "nodes": self.list_task_node_runs(task_id),
            "resume_from_node": checkpoint.get("resume_from_node"),
            "failure_context": checkpoint.get("failure_context", {}),
        }

    def as_user_payload(self, user) -> dict:
        return {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
        }

    def as_message_payload(self, message) -> dict:
        return {
            "id": message.id,
            "role": message.role,
            "message_type": message.message_type,
            "content": message.content,
            "metadata": message.metadata_json,
            "citations": message.citations_json,
            "created_at": message.created_at.isoformat(),
        }

    def as_chat_session_payload(self, session) -> dict:
        last_message_preview = ""
        recent_messages = self.list_messages(session.id)
        if recent_messages:
            last_message_preview = recent_messages[-1].content.replace("\n", " ").strip()[:120]
        return {
            "id": session.id,
            "title": session.title,
            "scope": session.scope,
            "status": session.status,
            "last_message_at": session.last_message_at.isoformat() if session.last_message_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "last_message_preview": last_message_preview,
            "memory_summary_text": session.memory_summary_text,
        }

    def as_inbox_payload(self, inbox) -> dict:
        return {
            "id": inbox.id,
            "title": inbox.title,
            "status": inbox.status,
            "summary": inbox.summary,
            "last_message_at": inbox.last_message_at.isoformat() if inbox.last_message_at else None,
        }

    def as_task_payload(self, task) -> dict:
        checkpoint = dict(task.checkpoint_json or {})
        return {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "current_node": task.current_node,
            "progress_percent": task.progress_percent,
            "detail": task.detail,
            "resume_from_node": checkpoint.get("resume_from_node"),
            "failure_context": checkpoint.get("failure_context", {}),
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }

    def as_workspace_payload(self, workspace) -> dict:
        return {
            "id": workspace.id,
            "name": workspace.name,
            "description": workspace.description,
            "status": workspace.status,
            "share_token": workspace.share_token,
            "created_at": workspace.created_at.isoformat(),
            "updated_at": workspace.updated_at.isoformat(),
        }

    def as_knowledge_file_payload(self, file_record) -> dict:
        return {
            "id": file_record.id,
            "title": file_record.title,
            "source_type": file_record.source_type,
            "source_url": file_record.source_url,
            "object_key": file_record.object_key,
            "parser_status": file_record.parser_status,
            "index_status": file_record.index_status,
            "metadata": file_record.metadata_json,
            "created_at": file_record.created_at.isoformat(),
            "updated_at": file_record.updated_at.isoformat(),
        }


memory_store = SQLBackedStore()
