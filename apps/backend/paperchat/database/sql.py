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


def ensure_database_exists() -> None:
    url = make_url(settings.mysql.endpoint)
    database_name = url.database
    if not database_name:
        return

    if not url.drivername.startswith("mysql"):
        return

    admin_url = url.set(database="mysql")
    admin_engine = create_engine(
        admin_url,
        pool_pre_ping=True,
        future=True,
    )
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


def init_database() -> None:
    from paperchat.database.models.tables import (  # noqa: F401
        PaperChatSessionRecord,
        PaperChatInboxConversationRecord,
        PaperChatKnowledgeFileRecord,
        PaperChatMessageRecord,
        PaperChatResearchTaskRecord,
        PaperChatUserRecord,
        PaperChatUserSessionRecord,
        PaperChatWorkspaceRecord,
    )

    ensure_database_exists()
    Base.metadata.create_all(bind=engine, checkfirst=True)
    ensure_runtime_columns()


def ensure_runtime_columns() -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "paperchat_chat_sessions" not in table_names:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("paperchat_chat_sessions")}
    alter_statements: list[str] = []

    if "memory_summary_text" not in existing_columns:
        alter_statements.append(
            "ALTER TABLE `paperchat_chat_sessions` "
            "ADD COLUMN `memory_summary_text` TEXT NULL"
        )
    if "last_summarized_message_id" not in existing_columns:
        alter_statements.append(
            "ALTER TABLE `paperchat_chat_sessions` "
            "ADD COLUMN `last_summarized_message_id` VARCHAR(36) NULL"
        )

    if "paperchat_research_tasks" in table_names:
        task_columns = {column["name"] for column in inspector.get_columns("paperchat_research_tasks")}
        if "payload_json" not in task_columns:
            alter_statements.append(
                "ALTER TABLE `paperchat_research_tasks` "
                "ADD COLUMN `payload_json` JSON NULL"
            )
        if "checkpoint_json" not in task_columns:
            alter_statements.append(
                "ALTER TABLE `paperchat_research_tasks` "
                "ADD COLUMN `checkpoint_json` JSON NULL"
            )

    if not alter_statements:
        return

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        for statement in alter_statements:
            connection.execute(text(statement))
