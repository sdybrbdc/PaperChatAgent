from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
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

    Base.metadata.create_all(bind=engine, checkfirst=True)
