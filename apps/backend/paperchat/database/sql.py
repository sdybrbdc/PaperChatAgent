from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from paperchat.settings import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(
    settings.mysql.endpoint,
    pool_pre_ping=True,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


LEGACY_DROP_ORDER = [
    "paperchat_research_tasks",
    "paperchat_knowledge_files",
    "paperchat_chat_sessions",
    "paperchat_workspaces",
    "paperchat_inbox_conversations",
]

CHAT_SCHEMA_REQUIRED_COLUMNS: dict[str, set[str]] = {
    "paperchat_conversations": {
        "id",
        "user_id",
        "title",
        "status",
        "title_finalized",
        "completed_turn_count",
        "last_message_preview",
        "last_message_at",
        "created_at",
        "updated_at",
    },
    "paperchat_messages": {
        "id",
        "conversation_id",
        "user_id",
        "role",
        "message_type",
        "content",
        "metadata_json",
        "citations_json",
        "created_at",
    },
    "paperchat_conversation_guidance_snapshots": {
        "conversation_id",
        "status",
        "headline",
        "sections_json",
        "draft_json",
        "source_message_id",
        "created_at",
        "updated_at",
    },
    "paperchat_conversation_realtime_events": {
        "id",
        "conversation_id",
        "event_type",
        "payload_json",
        "created_at",
    },
}


def ensure_database_exists() -> None:
    url = make_url(settings.mysql.endpoint)
    database_name = url.database
    if not database_name or not url.drivername.startswith("mysql"):
        return

    admin_url = url.set(database="mysql")
    admin_engine = create_engine(admin_url, pool_pre_ping=True, future=True)
    try:
        with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                    "DEFAULT CHARACTER SET utf8mb4 "
                    "DEFAULT COLLATE utf8mb4_unicode_ci"
                )
            )
    finally:
        admin_engine.dispose()


@contextmanager
def db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def drop_legacy_tables() -> None:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    statements = [
        f"DROP TABLE IF EXISTS `{table_name}`"
        for table_name in LEGACY_DROP_ORDER
        if table_name in existing
    ]
    for table_name, required_columns in CHAT_SCHEMA_REQUIRED_COLUMNS.items():
        if table_name not in existing:
            continue
        actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
        if not required_columns.issubset(actual_columns):
            statements.append(f"DROP TABLE IF EXISTS `{table_name}`")
    if not statements:
        return

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        try:
            for statement in statements:
                connection.execute(text(statement))
        finally:
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def init_database() -> None:
    from paperchat.database.models.tables import (  # noqa: F401
        PaperChatConversationGuidanceSnapshotRecord,
        PaperChatConversationRealtimeEventRecord,
        PaperChatConversationRecord,
        PaperChatMessageRecord,
        PaperChatUserRecord,
        PaperChatUserSessionRecord,
    )

    ensure_database_exists()
    drop_legacy_tables()
    Base.metadata.create_all(bind=engine, checkfirst=True)
