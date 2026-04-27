from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, desc, select

from paperchat.api.errcode import AppError
from paperchat.database.models import tables
from paperchat.database.sql import db_session


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _page(items: list[Any], *, limit: int, offset: int) -> tuple[list[Any], dict[str, Any]]:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    page_items = items[offset : offset + limit]
    return page_items, {
        "limit": limit,
        "offset": offset,
        "total": len(items),
        "has_more": offset + limit < len(items),
    }


@dataclass
class KnowledgeBaseRecord:
    id: str
    user_id: str
    name: str
    description: str = ""
    visibility: str = "private"
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class KnowledgeFileRecord:
    id: str
    knowledge_base_id: str
    user_id: str
    filename: str
    source_type: str
    source_uri: str = ""
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    status: str = "pending"
    title: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    chunk_count: int = 0
    error_message: str = ""
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class ConversationKnowledgeBindingRecord:
    conversation_id: str
    user_id: str
    knowledge_base_ids: list[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=utcnow)


class InMemoryKnowledgeRepository:
    """Temporary repository until the SQL tables are wired by the integration thread."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.knowledge_bases: dict[str, KnowledgeBaseRecord] = {}
        self.files: dict[str, KnowledgeFileRecord] = {}
        self.bindings: dict[str, ConversationKnowledgeBindingRecord] = {}

    def create_knowledge_base(
        self,
        *,
        user_id: str,
        name: str,
        description: str,
        visibility: str,
        metadata: dict[str, Any],
    ) -> KnowledgeBaseRecord:
        with self._lock:
            record = KnowledgeBaseRecord(
                id=str(uuid4()),
                user_id=user_id,
                name=name,
                description=description,
                visibility=visibility,
                metadata=dict(metadata),
            )
            self.knowledge_bases[record.id] = record
            return record

    def list_knowledge_bases(self, user_id: str, *, include_archived: bool = False) -> list[KnowledgeBaseRecord]:
        with self._lock:
            items = [
                item
                for item in self.knowledge_bases.values()
                if item.user_id == user_id and (include_archived or item.status != "archived")
            ]
            return sorted(items, key=lambda item: item.updated_at, reverse=True)

    def get_knowledge_base(self, knowledge_base_id: str) -> KnowledgeBaseRecord | None:
        with self._lock:
            return self.knowledge_bases.get(knowledge_base_id)

    def update_knowledge_base(self, knowledge_base_id: str, **changes: Any) -> KnowledgeBaseRecord | None:
        with self._lock:
            record = self.knowledge_bases.get(knowledge_base_id)
            if record is None:
                return None
            for key, value in changes.items():
                setattr(record, key, value)
            record.updated_at = utcnow()
            return record

    def add_file(
        self,
        *,
        user_id: str,
        knowledge_base_id: str,
        filename: str,
        source_type: str,
        source_uri: str,
        content_type: str,
        size_bytes: int,
        title: str,
        metadata: dict[str, Any],
    ) -> KnowledgeFileRecord:
        with self._lock:
            record = KnowledgeFileRecord(
                id=str(uuid4()),
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                filename=filename,
                source_type=source_type,
                source_uri=source_uri,
                content_type=content_type,
                size_bytes=size_bytes,
                title=title or filename,
                metadata=dict(metadata),
            )
            self.files[record.id] = record
            base = self.knowledge_bases.get(knowledge_base_id)
            if base is not None:
                base.updated_at = utcnow()
            return record

    def get_file(self, file_id: str) -> KnowledgeFileRecord | None:
        with self._lock:
            return self.files.get(file_id)

    def list_files(self, knowledge_base_id: str) -> list[KnowledgeFileRecord]:
        with self._lock:
            items = [item for item in self.files.values() if item.knowledge_base_id == knowledge_base_id]
            return sorted(items, key=lambda item: item.created_at, reverse=True)

    def list_files_for_bases(self, user_id: str, knowledge_base_ids: list[str]) -> list[KnowledgeFileRecord]:
        allowed = set(knowledge_base_ids)
        with self._lock:
            items = [
                item
                for item in self.files.values()
                if item.user_id == user_id and item.knowledge_base_id in allowed
            ]
            return sorted(items, key=lambda item: item.created_at, reverse=True)

    def update_file(self, file_id: str, **changes: Any) -> KnowledgeFileRecord | None:
        with self._lock:
            record = self.files.get(file_id)
            if record is None:
                return None
            for key, value in changes.items():
                setattr(record, key, value)
            record.updated_at = utcnow()
            return record

    def set_binding(
        self,
        *,
        user_id: str,
        conversation_id: str,
        knowledge_base_ids: list[str],
    ) -> ConversationKnowledgeBindingRecord:
        with self._lock:
            record = ConversationKnowledgeBindingRecord(
                conversation_id=conversation_id,
                user_id=user_id,
                knowledge_base_ids=list(knowledge_base_ids),
                updated_at=utcnow(),
            )
            self.bindings[conversation_id] = record
            return record

    def get_binding(self, conversation_id: str) -> ConversationKnowledgeBindingRecord | None:
        with self._lock:
            return self.bindings.get(conversation_id)


class SQLKnowledgeRepository:
    @property
    def available(self) -> bool:
        return all(
            hasattr(tables, name)
            for name in [
                "PaperChatKnowledgeBaseRecord",
                "PaperChatKnowledgeFileRecord",
                "PaperChatConversationKnowledgeBindingRecord",
            ]
        )

    def _base_from_record(self, record) -> KnowledgeBaseRecord:
        return KnowledgeBaseRecord(
            id=record.id,
            user_id=record.user_id,
            name=record.name,
            description=record.description,
            visibility="private",
            status=record.status,
            metadata={},
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _file_from_record(self, record) -> KnowledgeFileRecord:
        status = "indexed" if record.index_status == "indexed" else "failed" if record.index_status == "failed" else "pending"
        return KnowledgeFileRecord(
            id=record.id,
            knowledge_base_id=record.knowledge_base_id,
            user_id=record.user_id,
            filename=record.filename or record.title,
            source_type=record.source_type,
            source_uri=record.source_url,
            content_type=record.mime_type,
            size_bytes=int((record.metadata_json or {}).get("size_bytes") or 0),
            status=status,
            title=record.title,
            metadata=record.metadata_json or {},
            chunk_count=record.chunk_count,
            error_message=record.error_text,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def create_knowledge_base(
        self,
        *,
        user_id: str,
        name: str,
        description: str,
        visibility: str,
        metadata: dict[str, Any],
    ) -> KnowledgeBaseRecord:
        with db_session() as session:
            record = tables.PaperChatKnowledgeBaseRecord(
                user_id=user_id,
                name=name,
                description=description,
                status="active",
            )
            session.add(record)
            session.flush()
            return self._base_from_record(record)

    def list_knowledge_bases(self, user_id: str, *, include_archived: bool = False) -> list[KnowledgeBaseRecord]:
        with db_session() as session:
            statement = select(tables.PaperChatKnowledgeBaseRecord).where(
                tables.PaperChatKnowledgeBaseRecord.user_id == user_id
            )
            if not include_archived:
                statement = statement.where(tables.PaperChatKnowledgeBaseRecord.status != "archived")
            statement = statement.order_by(desc(tables.PaperChatKnowledgeBaseRecord.updated_at))
            return [self._base_from_record(record) for record in session.scalars(statement)]

    def get_knowledge_base(self, knowledge_base_id: str) -> KnowledgeBaseRecord | None:
        with db_session() as session:
            record = session.get(tables.PaperChatKnowledgeBaseRecord, knowledge_base_id)
            return self._base_from_record(record) if record else None

    def update_knowledge_base(self, knowledge_base_id: str, **changes: Any) -> KnowledgeBaseRecord | None:
        with db_session() as session:
            record = session.get(tables.PaperChatKnowledgeBaseRecord, knowledge_base_id)
            if record is None:
                return None
            for key, value in changes.items():
                if key in {"name", "description", "status"}:
                    setattr(record, key, value)
            record.updated_at = utcnow()
            session.flush()
            return self._base_from_record(record)

    def add_file(
        self,
        *,
        user_id: str,
        knowledge_base_id: str,
        filename: str,
        source_type: str,
        source_uri: str,
        content_type: str,
        size_bytes: int,
        title: str,
        metadata: dict[str, Any],
    ) -> KnowledgeFileRecord:
        metadata_json = {**metadata, "size_bytes": size_bytes}
        with db_session() as session:
            record = tables.PaperChatKnowledgeFileRecord(
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                source_type=source_type,
                title=title or filename,
                filename=filename,
                mime_type=content_type,
                source_url=source_uri,
                object_key=source_uri,
                parser_status="parsed",
                index_status="pending",
                metadata_json=metadata_json,
            )
            session.add(record)
            base = session.get(tables.PaperChatKnowledgeBaseRecord, knowledge_base_id)
            if base is not None:
                base.file_count += 1
                base.updated_at = utcnow()
            session.flush()
            return self._file_from_record(record)

    def get_file(self, file_id: str) -> KnowledgeFileRecord | None:
        with db_session() as session:
            record = session.get(tables.PaperChatKnowledgeFileRecord, file_id)
            return self._file_from_record(record) if record else None

    def list_files(self, knowledge_base_id: str) -> list[KnowledgeFileRecord]:
        with db_session() as session:
            records = session.scalars(
                select(tables.PaperChatKnowledgeFileRecord)
                .where(tables.PaperChatKnowledgeFileRecord.knowledge_base_id == knowledge_base_id)
                .order_by(desc(tables.PaperChatKnowledgeFileRecord.created_at))
            )
            return [self._file_from_record(record) for record in records]

    def list_files_for_bases(self, user_id: str, knowledge_base_ids: list[str]) -> list[KnowledgeFileRecord]:
        with db_session() as session:
            records = session.scalars(
                select(tables.PaperChatKnowledgeFileRecord)
                .where(
                    tables.PaperChatKnowledgeFileRecord.user_id == user_id,
                    tables.PaperChatKnowledgeFileRecord.knowledge_base_id.in_(knowledge_base_ids),
                )
                .order_by(desc(tables.PaperChatKnowledgeFileRecord.created_at))
            )
            return [self._file_from_record(record) for record in records]

    def update_file(self, file_id: str, **changes: Any) -> KnowledgeFileRecord | None:
        with db_session() as session:
            record = session.get(tables.PaperChatKnowledgeFileRecord, file_id)
            if record is None:
                return None
            if "status" in changes:
                record.index_status = "indexed" if changes["status"] == "indexed" else changes["status"]
            if "chunk_count" in changes:
                record.chunk_count = changes["chunk_count"]
            if "metadata" in changes:
                record.metadata_json = changes["metadata"]
            if "error_message" in changes:
                record.error_text = changes["error_message"]
            record.updated_at = utcnow()
            session.flush()
            base = session.get(tables.PaperChatKnowledgeBaseRecord, record.knowledge_base_id)
            if base is not None:
                base.indexed_file_count = len(
                    list(
                        session.scalars(
                            select(tables.PaperChatKnowledgeFileRecord).where(
                                tables.PaperChatKnowledgeFileRecord.knowledge_base_id == base.id,
                                tables.PaperChatKnowledgeFileRecord.index_status == "indexed",
                            )
                        )
                    )
                )
                base.updated_at = utcnow()
            session.flush()
            return self._file_from_record(record)

    def set_binding(
        self,
        *,
        user_id: str,
        conversation_id: str,
        knowledge_base_ids: list[str],
    ) -> ConversationKnowledgeBindingRecord:
        with db_session() as session:
            session.execute(
                delete(tables.PaperChatConversationKnowledgeBindingRecord).where(
                    tables.PaperChatConversationKnowledgeBindingRecord.conversation_id == conversation_id
                )
            )
            for knowledge_base_id in knowledge_base_ids:
                session.add(
                    tables.PaperChatConversationKnowledgeBindingRecord(
                        conversation_id=conversation_id,
                        knowledge_base_id=knowledge_base_id,
                        binding_type="manual",
                        status="active",
                    )
                )
            session.flush()
        return ConversationKnowledgeBindingRecord(
            conversation_id=conversation_id,
            user_id=user_id,
            knowledge_base_ids=list(knowledge_base_ids),
            updated_at=utcnow(),
        )

    def get_binding(self, conversation_id: str) -> ConversationKnowledgeBindingRecord | None:
        with db_session() as session:
            rows = session.execute(
                select(
                    tables.PaperChatConversationKnowledgeBindingRecord.knowledge_base_id,
                    tables.PaperChatKnowledgeBaseRecord.user_id,
                )
                .join(
                    tables.PaperChatKnowledgeBaseRecord,
                    tables.PaperChatConversationKnowledgeBindingRecord.knowledge_base_id
                    == tables.PaperChatKnowledgeBaseRecord.id,
                )
                .where(
                    tables.PaperChatConversationKnowledgeBindingRecord.conversation_id == conversation_id,
                    tables.PaperChatConversationKnowledgeBindingRecord.status == "active",
                )
            ).all()
        if not rows:
            return None
        return ConversationKnowledgeBindingRecord(
            conversation_id=conversation_id,
            user_id=str(rows[0][1]),
            knowledge_base_ids=[str(row[0]) for row in rows],
            updated_at=utcnow(),
        )


class KnowledgeService:
    def __init__(self, repository: InMemoryKnowledgeRepository | SQLKnowledgeRepository | None = None) -> None:
        sql_repository = SQLKnowledgeRepository()
        self.repository = repository or (sql_repository if sql_repository.available else InMemoryKnowledgeRepository())

    def _require_base(self, user_id: str, knowledge_base_id: str) -> KnowledgeBaseRecord:
        record = self.repository.get_knowledge_base(knowledge_base_id)
        if record is None or record.user_id != user_id:
            raise AppError(status_code=404, code="KNOWLEDGE_BASE_NOT_FOUND", message="知识库不存在")
        return record

    def _require_file(self, user_id: str, file_id: str) -> KnowledgeFileRecord:
        record = self.repository.get_file(file_id)
        if record is None or record.user_id != user_id:
            raise AppError(status_code=404, code="KNOWLEDGE_FILE_NOT_FOUND", message="知识文件不存在")
        return record

    def _validate_bases(self, user_id: str, knowledge_base_ids: list[str]) -> list[str]:
        unique_ids = list(dict.fromkeys(knowledge_base_ids))
        for knowledge_base_id in unique_ids:
            self._require_base(user_id, knowledge_base_id)
        return unique_ids

    def _base_payload(self, record: KnowledgeBaseRecord) -> dict[str, Any]:
        files = self.repository.list_files(record.id)
        indexed_count = sum(1 for item in files if item.status == "indexed")
        return {
            "id": record.id,
            "user_id": record.user_id,
            "name": record.name,
            "description": record.description,
            "visibility": record.visibility,
            "status": record.status,
            "metadata": record.metadata,
            "file_count": len(files),
            "indexed_file_count": indexed_count,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }

    @staticmethod
    def _file_payload(record: KnowledgeFileRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "knowledge_base_id": record.knowledge_base_id,
            "user_id": record.user_id,
            "filename": record.filename,
            "original_filename": record.filename,
            "source_type": record.source_type,
            "source_uri": record.source_uri,
            "mime_type": record.content_type,
            "content_type": record.content_type,
            "size_bytes": record.size_bytes,
            "status": record.status,
            "parser_status": "parsed" if record.status == "indexed" else record.status,
            "index_status": record.status,
            "title": record.title,
            "metadata": record.metadata,
            "chunk_count": record.chunk_count,
            "error_message": record.error_message,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }

    @staticmethod
    def _binding_payload(record: ConversationKnowledgeBindingRecord) -> dict[str, Any]:
        return {
            "conversation_id": record.conversation_id,
            "knowledge_base_ids": record.knowledge_base_ids,
            "updated_at": record.updated_at.isoformat(),
        }

    def list_knowledge_bases_payload(
        self,
        user_id: str,
        *,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        items = self.repository.list_knowledge_bases(user_id, include_archived=include_archived)
        page_items, paging = _page(items, limit=limit, offset=offset)
        return {
            "items": [self._base_payload(item) for item in page_items],
            "paging": paging,
        }

    def create_knowledge_base_payload(
        self,
        user_id: str,
        *,
        name: str,
        description: str = "",
        visibility: str = "private",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = self.repository.create_knowledge_base(
            user_id=user_id,
            name=name.strip(),
            description=description,
            visibility=visibility,
            metadata=metadata or {},
        )
        return self._base_payload(record)

    def get_knowledge_base_payload(self, user_id: str, knowledge_base_id: str) -> dict[str, Any]:
        record = self._require_base(user_id, knowledge_base_id)
        return {
            **self._base_payload(record),
            "files": [self._file_payload(item) for item in self.repository.list_files(knowledge_base_id)],
        }

    def update_knowledge_base_payload(
        self,
        user_id: str,
        knowledge_base_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        visibility: str | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_base(user_id, knowledge_base_id)
        changes = {
            key: value
            for key, value in {
                "name": name.strip() if isinstance(name, str) else name,
                "description": description,
                "visibility": visibility,
                "status": status,
                "metadata": metadata,
            }.items()
            if value is not None
        }
        record = self.repository.update_knowledge_base(knowledge_base_id, **changes)
        if record is None:
            raise AppError(status_code=404, code="KNOWLEDGE_BASE_NOT_FOUND", message="知识库不存在")
        return self._base_payload(record)

    def list_files_payload(
        self,
        user_id: str,
        knowledge_base_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        self._require_base(user_id, knowledge_base_id)
        items = self.repository.list_files(knowledge_base_id)
        page_items, paging = _page(items, limit=limit, offset=offset)
        return {
            "items": [self._file_payload(item) for item in page_items],
            "paging": paging,
        }

    def create_upload_placeholder_payload(
        self,
        user_id: str,
        knowledge_base_id: str,
        *,
        filename: str,
        content_type: str,
        size_bytes: int,
        source_uri: str = "",
        title: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_base(user_id, knowledge_base_id)
        record = self.repository.add_file(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            source_type="upload",
            source_uri=source_uri,
            content_type=content_type,
            size_bytes=size_bytes,
            title=title,
            metadata=metadata or {},
        )
        return self._file_payload(record)

    def create_arxiv_import_placeholder_payload(
        self,
        user_id: str,
        knowledge_base_id: str,
        *,
        arxiv_id: str,
        title: str = "",
        authors: list[str] | None = None,
        abstract: str = "",
        pdf_url: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_base(user_id, knowledge_base_id)
        arxiv_id = arxiv_id.strip()
        file_metadata = {
            **(metadata or {}),
            "arxiv_id": arxiv_id,
            "authors": authors or [],
            "abstract": abstract,
        }
        record = self.repository.add_file(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            filename=f"arxiv-{arxiv_id}.pdf",
            source_type="arxiv",
            source_uri=pdf_url or f"https://arxiv.org/pdf/{arxiv_id}",
            content_type="application/pdf",
            size_bytes=0,
            title=title or f"arXiv {arxiv_id}",
            metadata=file_metadata,
        )
        return self._file_payload(record)

    def bind_conversation_payload(
        self,
        user_id: str,
        conversation_id: str,
        *,
        knowledge_base_ids: list[str],
    ) -> dict[str, Any]:
        valid_ids = self._validate_bases(user_id, knowledge_base_ids)
        record = self.repository.set_binding(
            user_id=user_id,
            conversation_id=conversation_id,
            knowledge_base_ids=valid_ids,
        )
        return self._binding_payload(record)

    def get_conversation_binding_payload(self, user_id: str, conversation_id: str) -> dict[str, Any]:
        record = self.repository.get_binding(conversation_id)
        if record is None or record.user_id != user_id:
            record = self.repository.set_binding(user_id=user_id, conversation_id=conversation_id, knowledge_base_ids=[])
        return self._binding_payload(record)

    def resolve_retrieval_scope(
        self,
        *,
        user_id: str,
        knowledge_base_ids: list[str] | None = None,
        conversation_id: str | None = None,
    ) -> list[str]:
        if knowledge_base_ids:
            return self._validate_bases(user_id, knowledge_base_ids)
        if conversation_id:
            binding = self.repository.get_binding(conversation_id)
            if binding is not None and binding.user_id == user_id:
                return self._validate_bases(user_id, binding.knowledge_base_ids)
        return []

    def list_files_for_retrieval(self, user_id: str, knowledge_base_ids: list[str]) -> list[dict[str, Any]]:
        valid_ids = self._validate_bases(user_id, knowledge_base_ids)
        return [self._file_payload(item) for item in self.repository.list_files_for_bases(user_id, valid_ids)]

    def mark_file_indexed(
        self,
        user_id: str,
        file_id: str,
        *,
        chunk_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = self._require_file(user_id, file_id)
        next_metadata = dict(record.metadata)
        next_metadata.update(metadata or {})
        updated = self.repository.update_file(
            file_id,
            status="indexed",
            chunk_count=chunk_count,
            metadata=next_metadata,
            error_message="",
        )
        if updated is None:
            raise AppError(status_code=404, code="KNOWLEDGE_FILE_NOT_FOUND", message="知识文件不存在")
        return self._file_payload(updated)


knowledge_service = KnowledgeService()
