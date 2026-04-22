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
class InboxConversation:
    id: str
    user_id: str
    title: str = "默认收件箱会话"
    status: str = "active"
    summary: str = ""
    last_message_at: datetime | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class ChatSession:
    id: str
    user_id: str
    title: str
    scope: str
    status: str = "active"
    workspace_id: str | None = None
    inbox_conversation_id: str | None = None
    last_message_at: datetime | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class ResearchWorkspace:
    id: str
    user_id: str
    name: str
    description: str = ""
    status: str = "active"
    share_token: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class Message:
    id: str
    session_id: str
    user_id: str | None
    role: str
    message_type: str
    content: str
    metadata: dict = field(default_factory=dict)
    citations: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class ResearchTask:
    id: str
    user_id: str
    workspace_id: str
    title: str
    status: str = "queued"
    current_node: str | None = None
    progress_percent: float = 0.0
    detail: str = ""
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
