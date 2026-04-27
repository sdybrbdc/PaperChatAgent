from __future__ import annotations

from datetime import datetime, timezone

from paperchat.database.models.tables import (
    PaperChatModelInvocationLogRecord,
    PaperChatModelProviderRecord,
    PaperChatModelRouteConfigRecord,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


PaperChatModelRouteRecord = PaperChatModelRouteConfigRecord
PaperChatModelUsageLogRecord = PaperChatModelInvocationLogRecord

__all__ = [
    "PaperChatModelInvocationLogRecord",
    "PaperChatModelProviderRecord",
    "PaperChatModelRouteConfigRecord",
    "PaperChatModelRouteRecord",
    "PaperChatModelUsageLogRecord",
    "utcnow",
]
