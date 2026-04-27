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
    "paperchat_conversation_memories": {
        "conversation_id",
        "summary_text",
        "key_points_json",
        "user_preferences_json",
        "open_questions_json",
        "compressed_message_count",
        "source_message_id",
        "created_at",
        "updated_at",
    },
    "paperchat_user_memories": {
        "id",
        "user_id",
        "memory_type",
        "title",
        "content",
        "tags_json",
        "confidence",
        "memory_fingerprint",
        "source_conversation_id",
        "source_message_id",
        "active",
        "last_observed_at",
        "created_at",
        "updated_at",
    },
    "paperchat_agent_workflows": {
        "id",
        "slug",
        "name",
        "description",
        "source_type",
        "status",
        "version",
        "definition_json",
        "created_at",
        "updated_at",
    },
    "paperchat_agent_node_config_overrides": {
        "id",
        "user_id",
        "workflow_id",
        "node_id",
        "executor_key",
        "fallback_executor_key",
        "model_slot",
        "config_json",
        "created_at",
        "updated_at",
    },
    "paperchat_research_tasks": {
        "id",
        "user_id",
        "conversation_id",
        "workflow_id",
        "title",
        "status",
        "current_node",
        "progress",
        "summary",
        "failed_reason",
        "created_at",
        "updated_at",
        "completed_at",
    },
    "paperchat_workflow_runs": {
        "id",
        "task_id",
        "user_id",
        "conversation_id",
        "workflow_id",
        "status",
        "current_node",
        "input_json",
        "output_json",
        "checkpoint_json",
        "error_json",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    },
    "paperchat_workflow_node_runs": {
        "id",
        "workflow_run_id",
        "node_id",
        "parent_node_id",
        "title",
        "status",
        "detail",
        "progress",
        "input_json",
        "output_json",
        "metadata_json",
        "error_text",
        "sort_order",
        "started_at",
        "completed_at",
    },
    "paperchat_task_artifacts": {
        "id",
        "task_id",
        "workflow_run_id",
        "artifact_type",
        "title",
        "content_text",
        "metadata_json",
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
        PaperChatAgentNodeConfigOverrideRecord,
        PaperChatAgentWorkflowRecord,
        PaperChatConversationGuidanceSnapshotRecord,
        PaperChatConversationMemoryRecord,
        PaperChatConversationRealtimeEventRecord,
        PaperChatConversationRecord,
        PaperChatMessageRecord,
        PaperChatResearchTaskRecord,
        PaperChatTaskArtifactRecord,
        PaperChatUserMemoryRecord,
        PaperChatUserRecord,
        PaperChatUserSessionRecord,
        PaperChatWorkflowNodeRunRecord,
        PaperChatWorkflowRunRecord,
    )

    ensure_database_exists()
    drop_legacy_tables()
    Base.metadata.create_all(bind=engine, checkfirst=True)

    from paperchat.services.agents import agent_service

    agent_service.ensure_builtin_workflows()
