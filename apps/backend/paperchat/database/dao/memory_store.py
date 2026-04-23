from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from sqlalchemy import desc, select

from paperchat.database.models.tables import (
    PaperChatConversationGuidanceSnapshotRecord,
    PaperChatConversationRealtimeEventRecord,
    PaperChatConversationRecord,
    PaperChatMessageRecord,
    PaperChatUserRecord,
    PaperChatUserSessionRecord,
)
from paperchat.database.sql import db_session


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_value(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


DEFAULT_GUIDANCE_PAYLOAD = {
    "status": "casual_chat",
    "headline": "你可以先像普通聊天一样交流问题，系统会在对话逐渐收敛后给出更专业的研究提示。",
    "sections": [
        {
            "key": "casual_hint",
            "title": "当前判断",
            "style": "compact",
            "text": "普通交流中，先把问题说清楚即可。",
            "items": [],
        }
    ],
    "draft": None,
}


class SQLBackedStore:
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

    def create_conversation(self, *, user_id: str, title: str = "新聊天"):
        with db_session() as session:
            conversation = PaperChatConversationRecord(user_id=user_id, title=title)
            session.add(conversation)
            session.flush()
            snapshot = PaperChatConversationGuidanceSnapshotRecord(
                conversation_id=conversation.id,
                status=DEFAULT_GUIDANCE_PAYLOAD["status"],
                headline=DEFAULT_GUIDANCE_PAYLOAD["headline"],
                sections_json=list(DEFAULT_GUIDANCE_PAYLOAD["sections"]),
                draft_json=None,
            )
            session.add(snapshot)
            session.flush()
            return conversation

    def get_conversation(self, conversation_id: str):
        with db_session() as session:
            return session.get(PaperChatConversationRecord, conversation_id)

    def update_conversation(self, conversation_id: str, **changes):
        with db_session() as session:
            conversation = session.get(PaperChatConversationRecord, conversation_id)
            if conversation is None:
                return None
            for key, value in changes.items():
                setattr(conversation, key, value)
            conversation.updated_at = utcnow()
            session.flush()
            return conversation

    def increment_completed_turn(self, conversation_id: str):
        with db_session() as session:
            conversation = session.get(PaperChatConversationRecord, conversation_id)
            if conversation is None:
                return None
            conversation.completed_turn_count += 1
            conversation.updated_at = utcnow()
            session.flush()
            return conversation

    def finalize_conversation_title(self, conversation_id: str, title: str):
        with db_session() as session:
            conversation = session.get(PaperChatConversationRecord, conversation_id)
            if conversation is None:
                return None
            conversation.title = title
            conversation.title_finalized = True
            conversation.updated_at = utcnow()
            session.flush()
            return conversation

    def list_conversations(self, user_id: str):
        with db_session() as session:
            return list(
                session.scalars(
                    select(PaperChatConversationRecord)
                    .where(PaperChatConversationRecord.user_id == user_id)
                    .order_by(desc(PaperChatConversationRecord.updated_at))
                )
            )

    def add_message(
        self,
        *,
        conversation_id: str,
        user_id: str | None,
        role: str,
        message_type: str,
        content: str,
        metadata: dict | None = None,
        citations: list[dict] | None = None,
    ):
        with db_session() as session:
            message = PaperChatMessageRecord(
                conversation_id=conversation_id,
                user_id=user_id,
                role=role,
                message_type=message_type,
                content=content,
                metadata_json=metadata or {},
                citations_json=citations or [],
            )
            session.add(message)
            session.flush()

            conversation = session.get(PaperChatConversationRecord, conversation_id)
            if conversation is not None:
                conversation.last_message_at = message.created_at
                conversation.updated_at = message.created_at
                preview = content.replace("\n", " ").strip()
                if preview:
                    conversation.last_message_preview = preview[:120]
            session.flush()
            return message

    def list_messages(self, conversation_id: str):
        with db_session() as session:
            return list(
                session.scalars(
                    select(PaperChatMessageRecord)
                    .where(PaperChatMessageRecord.conversation_id == conversation_id)
                    .order_by(PaperChatMessageRecord.created_at.asc())
                )
            )

    def get_recent_context_messages(self, conversation_id: str, limit: int):
        messages = self.list_messages(conversation_id)
        return messages[-limit:]

    def get_guidance_snapshot(self, conversation_id: str):
        with db_session() as session:
            return session.get(PaperChatConversationGuidanceSnapshotRecord, conversation_id)

    def upsert_guidance_snapshot(
        self,
        conversation_id: str,
        *,
        status: str,
        headline: str,
        sections: list[dict[str, Any]],
        draft: dict[str, Any] | None,
        source_message_id: str | None = None,
    ):
        with db_session() as session:
            snapshot = session.get(PaperChatConversationGuidanceSnapshotRecord, conversation_id)
            if snapshot is None:
                snapshot = PaperChatConversationGuidanceSnapshotRecord(conversation_id=conversation_id)
                session.add(snapshot)
            snapshot.status = status
            snapshot.headline = headline
            snapshot.sections_json = sections
            snapshot.draft_json = draft
            snapshot.source_message_id = source_message_id
            snapshot.updated_at = utcnow()
            session.flush()
            return snapshot

    def update_guidance_draft(self, conversation_id: str, *, draft: dict[str, Any], status: str = "draft_ready"):
        with db_session() as session:
            snapshot = session.get(PaperChatConversationGuidanceSnapshotRecord, conversation_id)
            if snapshot is None:
                snapshot = PaperChatConversationGuidanceSnapshotRecord(conversation_id=conversation_id)
                session.add(snapshot)
                snapshot.headline = DEFAULT_GUIDANCE_PAYLOAD["headline"]
                snapshot.sections_json = list(DEFAULT_GUIDANCE_PAYLOAD["sections"])
            snapshot.draft_json = draft
            snapshot.status = status
            snapshot.updated_at = utcnow()
            session.flush()
            return snapshot

    def append_realtime_event(self, *, conversation_id: str, event_type: str, payload: dict[str, Any]):
        with db_session() as session:
            record = PaperChatConversationRealtimeEventRecord(
                conversation_id=conversation_id,
                event_type=event_type,
                payload_json=payload,
            )
            session.add(record)
            session.flush()
            return record

    def as_user_payload(self, user) -> dict[str, Any]:
        return {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "status": user.status,
        }

    def as_conversation_payload(self, conversation) -> dict[str, Any]:
        return {
            "id": conversation.id,
            "title": conversation.title,
            "status": conversation.status,
            "title_finalized": conversation.title_finalized,
            "completed_turn_count": conversation.completed_turn_count,
            "last_message_preview": conversation.last_message_preview,
            "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            "created_at": conversation.created_at.isoformat(),
        }

    def as_message_payload(self, message) -> dict[str, Any]:
        return {
            "id": message.id,
            "role": message.role,
            "message_type": message.message_type,
            "content": message.content,
            "metadata": message.metadata_json or {},
            "citations": message.citations_json or [],
            "created_at": message.created_at.isoformat(),
        }

    def as_guidance_payload(self, snapshot) -> dict[str, Any]:
        return {
            "status": snapshot.status,
            "headline": snapshot.headline,
            "sections": snapshot.sections_json or list(DEFAULT_GUIDANCE_PAYLOAD["sections"]),
            "draft": snapshot.draft_json,
            "updated_at": snapshot.updated_at.isoformat() if snapshot.updated_at else None,
            "source_message_id": snapshot.source_message_id,
        }


memory_store = SQLBackedStore()
