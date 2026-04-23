from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    display_name: str
    avatar_url: str = ""
    status: str = "active"
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class UserSession:
    id: str
    user_id: str
    refresh_token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class Conversation:
    id: str
    user_id: str
    title: str
    status: str = "active"
    title_finalized: bool = False
    completed_turn_count: int = 0
    last_message_preview: str = ""
    last_message_at: datetime | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class Message:
    id: str
    conversation_id: str
    user_id: str | None
    role: str
    message_type: str
    content: str
    metadata: dict = field(default_factory=dict)
    citations: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class ConversationGuidanceSnapshot:
    conversation_id: str
    status: str = "casual_chat"
    headline: str = ""
    sections: list[dict] = field(default_factory=list)
    draft: dict | None = None
    source_message_id: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class ConversationRealtimeEvent:
    id: str
    conversation_id: str
    event_type: str
    payload: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)
