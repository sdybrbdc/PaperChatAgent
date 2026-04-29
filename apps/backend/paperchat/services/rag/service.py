from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import chromadb
import fitz
from chromadb.config import Settings as ChromaSettings
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.chroma import ChromaVectorStore
from sqlalchemy import delete, desc, select

from paperchat.api.errcode import AppError
from paperchat.database.models import tables
from paperchat.database.sql import db_session
from paperchat.services.knowledge import knowledge_service
from paperchat.services.storage import storage_service
from paperchat.settings import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _short_error(error: Exception) -> str:
    return str(error)[:2000]


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _vector_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    cleaned: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = json.dumps(value, ensure_ascii=False)
    return cleaned


def _safe_collection_name(knowledge_base_id: str) -> str:
    prefix = get_settings().rag.collection_prefix.strip() or "paperchat_kb"
    return f"{prefix}_{knowledge_base_id}".replace("-", "_")


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


@dataclass
class ParsedDocument:
    text: str
    documents: list[Document]
    parser_name: str


class RagService:
    def _effective_top_k(self, requested: int | None, *, default: int, maximum: int) -> int:
        return max(1, min(requested if requested is not None else default, max(1, maximum)))

    def _persist_dir(self) -> str:
        settings = get_settings()
        path = Path(settings.vector_db.persist_dir)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[3] / path
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def _chroma_client(self):
        return chromadb.PersistentClient(
            path=self._persist_dir(),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def _collection(self, knowledge_base_id: str):
        return self._chroma_client().get_or_create_collection(name=_safe_collection_name(knowledge_base_id))

    def _embedding_model(self) -> OpenAIEmbedding:
        settings = get_settings()
        config = settings.multi_models.embedding
        api_key = config.api_key.strip()
        if not api_key or api_key.startswith("${"):
            raise AppError(
                status_code=500,
                code="RAG_EMBEDDING_NOT_CONFIGURED",
                message="Embedding 模型未配置，请设置 multi_models.embedding.api_key",
            )
        return OpenAIEmbedding(
            api_key=api_key,
            api_base=config.base_url or None,
            model_name=config.model_name or "text-embedding-ada-002",
            embed_batch_size=max(1, settings.rag.embedding_batch_size),
        )

    def _llm(self) -> OpenAI:
        settings = get_settings()
        config = settings.multi_models.conversation_model
        api_key = config.api_key.strip()
        if not api_key or api_key.startswith("${"):
            raise AppError(
                status_code=500,
                code="RAG_LLM_NOT_CONFIGURED",
                message="对话模型未配置，请设置 multi_models.conversation_model.api_key",
            )
        return OpenAI(
            api_key=api_key,
            api_base=config.base_url or None,
            model=config.model_name or "gpt-4o-mini",
            temperature=0.1,
        )

    def _parse_documents(self, *, file_payload: dict[str, Any], data: bytes) -> ParsedDocument:
        filename = file_payload.get("filename") or file_payload.get("title") or "document"
        content_type = str(file_payload.get("content_type") or file_payload.get("mime_type") or "").lower()
        suffix = Path(filename).suffix.lower()
        base_metadata = {
            "knowledge_base_id": file_payload["knowledge_base_id"],
            "file_id": file_payload["id"],
            "filename": filename,
            "source_type": file_payload.get("source_type") or "upload",
            "object_key": file_payload.get("object_key") or "",
            "source_uri": file_payload.get("source_uri") or "",
        }

        if suffix in {".md", ".markdown"} or "markdown" in content_type:
            text = _decode_text(data)
            return ParsedDocument(
                text=text,
                documents=self._markdown_documents(text, base_metadata),
                parser_name="markdown",
            )
        if suffix in {".txt", ".text"} or content_type.startswith("text/"):
            text = _decode_text(data)
            return ParsedDocument(
                text=text,
                documents=[Document(text=text, metadata={**base_metadata, "section_title": "", "page_no": None})],
                parser_name="text",
            )
        if suffix == ".pdf" or content_type == "application/pdf":
            return self._pdf_documents(data, base_metadata)

        raise AppError(
            status_code=400,
            code="RAG_UNSUPPORTED_FILE_TYPE",
            message=f"暂不支持解析 {filename}，第一版仅支持 Markdown、TXT、PDF",
        )

    def _markdown_documents(self, text: str, base_metadata: dict[str, Any]) -> list[Document]:
        sections: list[tuple[str, list[str]]] = []
        current_title = ""
        current_lines: list[str] = []
        for line in text.splitlines():
            match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if match and current_lines:
                sections.append((current_title, current_lines))
                current_title = match.group(2).strip()
                current_lines = [line]
            else:
                if match:
                    current_title = match.group(2).strip()
                current_lines.append(line)
        if current_lines:
            sections.append((current_title, current_lines))

        documents = []
        for title, lines in sections or [("", text.splitlines())]:
            section_text = "\n".join(lines).strip()
            if not section_text:
                continue
            documents.append(
                Document(text=section_text, metadata={**base_metadata, "section_title": title, "page_no": None})
            )
        return documents or [Document(text=text, metadata={**base_metadata, "section_title": "", "page_no": None})]

    def _pdf_documents(self, data: bytes, base_metadata: dict[str, Any]) -> ParsedDocument:
        pdf = fitz.open(stream=data, filetype="pdf")
        documents: list[Document] = []
        rendered_pages: list[str] = []
        for index, page in enumerate(pdf, start=1):
            page_text = page.get_text("text").strip()
            if not page_text:
                continue
            rendered_pages.append(f"\n\n<!-- page:{index} -->\n\n{page_text}")
            documents.append(
                Document(
                    text=page_text,
                    metadata={**base_metadata, "section_title": f"Page {index}", "page_no": index},
                )
            )
        text = "\n".join(rendered_pages).strip()
        if not documents:
            raise AppError(status_code=400, code="RAG_PARSE_EMPTY", message="PDF 未解析到可索引文本")
        return ParsedDocument(text=text, documents=documents, parser_name="pymupdf")

    def _split_documents(self, documents: list[Document]) -> list[TextNode]:
        rag_settings = get_settings().rag
        chunk_size = max(1, rag_settings.chunk_size)
        chunk_overlap = max(0, min(rag_settings.chunk_overlap, chunk_size - 1))
        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            include_metadata=True,
            include_prev_next_rel=True,
        )
        nodes = splitter.get_nodes_from_documents(documents)
        return [node for node in nodes if node.get_content(metadata_mode="none").strip()]

    def _chunk_payload(self, record) -> dict[str, Any]:
        return {
            "id": record.id,
            "knowledge_base_id": record.knowledge_base_id,
            "knowledge_file_id": record.knowledge_file_id,
            "chunk_index": record.chunk_index,
            "content": record.content,
            "content_hash": record.content_hash,
            "page_no": record.page_no,
            "section_title": record.section_title,
            "vector_collection": record.vector_collection,
            "vector_doc_id": record.vector_doc_id,
            "token_count": record.token_count,
            "locator": record.locator_json or {},
            "metadata": record.metadata_json or {},
            "created_at": record.created_at.isoformat(),
        }

    def _source_from_chunk(self, chunk: dict[str, Any]) -> dict[str, Any]:
        metadata = chunk["metadata"]
        return {
            "file_id": chunk["knowledge_file_id"],
            "knowledge_base_id": chunk["knowledge_base_id"],
            "title": str(metadata.get("title") or metadata.get("filename") or ""),
            "filename": str(metadata.get("filename") or ""),
            "source_type": str(metadata.get("source_type") or "upload"),
            "source_uri": str(metadata.get("source_uri") or ""),
            "metadata": {
                **metadata,
                "chunk_id": chunk["id"],
                "page_no": chunk["page_no"],
                "section_title": chunk["section_title"],
            },
        }

    def _result_from_chunk(self, chunk: dict[str, Any], score: float) -> dict[str, Any]:
        return {
            "id": chunk["id"],
            "chunk_id": chunk["id"],
            "text": chunk["content"],
            "score": round(float(score), 4),
            "source": self._source_from_chunk(chunk),
            "metadata": {
                **chunk["metadata"],
                "page_no": chunk["page_no"],
                "section_title": chunk["section_title"],
                "chunk_index": chunk["chunk_index"],
            },
        }

    def create_index_job(self, *, user_id: str, file_id: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        knowledge_service._require_file(user_id, file_id)
        with db_session() as session:
            job = tables.PaperChatRagIndexJobRecord(
                knowledge_file_id=file_id,
                user_id=user_id,
                status="queued",
                stage="queued",
                progress=0,
                metadata_json=metadata or {},
            )
            session.add(job)
            session.flush()
            return self._job_payload(job)

    def _job_payload(self, job) -> dict[str, Any]:
        return {
            "id": job.id,
            "knowledge_file_id": job.knowledge_file_id,
            "user_id": job.user_id,
            "status": job.status,
            "stage": job.stage,
            "progress": job.progress,
            "parser_name": job.parser_name,
            "embedding_route_key": job.embedding_route_key,
            "error_text": job.error_text,
            "metadata": job.metadata_json or {},
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
        }

    def _update_job(self, job_id: str, **changes: Any) -> None:
        with db_session() as session:
            job = session.get(tables.PaperChatRagIndexJobRecord, job_id)
            if job is None:
                return
            for key, value in changes.items():
                setattr(job, key, value)
            job.updated_at = utcnow()
            session.flush()

    def _latest_job(self, file_id: str) -> dict[str, Any] | None:
        with db_session() as session:
            job = session.scalars(
                select(tables.PaperChatRagIndexJobRecord)
                .where(tables.PaperChatRagIndexJobRecord.knowledge_file_id == file_id)
                .order_by(desc(tables.PaperChatRagIndexJobRecord.created_at))
                .limit(1)
            ).first()
            return self._job_payload(job) if job else None

    def run_index_job(self, *, user_id: str, file_id: str, job_id: str) -> None:
        try:
            file_payload = knowledge_service._file_payload(knowledge_service._require_file(user_id, file_id))
            self._update_job(job_id, status="running", stage="parsing", progress=10, started_at=utcnow())
            knowledge_service.repository.update_file(
                file_id,
                parser_status="parsing",
                index_status="pending",
                error_message="",
            )

            object_key = file_payload.get("object_key") or ""
            if not object_key:
                raise AppError(status_code=400, code="RAG_FILE_OBJECT_MISSING", message="文件缺少 MinIO object_key")
            data = storage_service.download_bytes(object_key)
            parsed = self._parse_documents(file_payload=file_payload, data=data)
            parsed_key = f"parsed/{user_id}/{file_payload['knowledge_base_id']}/{file_id}.md"
            storage_service.upload_text(object_key=parsed_key, text=parsed.text)
            self._update_job(job_id, stage="chunking", progress=35, parser_name=parsed.parser_name)
            knowledge_service.repository.update_file(
                file_id,
                parser_status="parsed",
                parsed_text_object_key=parsed_key,
            )

            nodes = self._split_documents(parsed.documents)
            if not nodes:
                raise AppError(status_code=400, code="RAG_PARSE_EMPTY", message="没有可索引的文本片段")
            db_nodes = self._replace_chunks(file_payload=file_payload, nodes=nodes)
            self._update_job(job_id, stage="embedding", progress=65)

            collection = self._collection(file_payload["knowledge_base_id"])
            try:
                collection.delete(where={"file_id": file_id})
            except Exception:
                pass
            vector_store = ChromaVectorStore(chroma_collection=collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            VectorStoreIndex(db_nodes, storage_context=storage_context, embed_model=self._embedding_model())

            self._update_job(job_id, status="completed", stage="completed", progress=100, completed_at=utcnow())
            knowledge_service.repository.update_file(
                file_id,
                parser_status="parsed",
                index_status="indexed",
                chunk_count=len(db_nodes),
                metadata={**file_payload.get("metadata", {}), "indexer": "llamaindex", "indexed_at": utcnow().isoformat()},
                error_message="",
            )
        except Exception as error:
            message = error.message if isinstance(error, AppError) else _short_error(error)
            self._update_job(
                job_id,
                status="failed",
                stage="failed",
                progress=0,
                error_text=message,
                completed_at=utcnow(),
            )
            knowledge_service.repository.update_file(
                file_id,
                parser_status="failed",
                index_status="failed",
                error_message=message,
            )

    def _replace_chunks(self, *, file_payload: dict[str, Any], nodes: list[TextNode]) -> list[TextNode]:
        knowledge_base_id = file_payload["knowledge_base_id"]
        file_id = file_payload["id"]
        collection_name = _safe_collection_name(knowledge_base_id)
        with db_session() as session:
            session.execute(
                delete(tables.PaperChatKnowledgeChunkRecord).where(
                    tables.PaperChatKnowledgeChunkRecord.knowledge_file_id == file_id
                )
            )
            session.flush()
            rows = []
            for index, node in enumerate(nodes):
                content = node.get_content(metadata_mode="none").strip()
                metadata = {
                    **node.metadata,
                    "title": file_payload.get("title") or file_payload.get("filename") or "",
                    "filename": file_payload.get("filename") or "",
                    "source_uri": file_payload.get("source_uri") or "",
                    "source_type": file_payload.get("source_type") or "upload",
                    "file_id": file_id,
                    "knowledge_base_id": knowledge_base_id,
                    "chunk_index": index,
                }
                row = tables.PaperChatKnowledgeChunkRecord(
                    knowledge_base_id=knowledge_base_id,
                    knowledge_file_id=file_id,
                    chunk_index=index,
                    content=content,
                    content_hash=_content_hash(content),
                    page_no=metadata.get("page_no"),
                    section_title=str(metadata.get("section_title") or ""),
                    vector_collection=collection_name,
                    vector_doc_id=str(uuid4()),
                    token_count=max(1, len(content) // 4),
                    locator_json={
                        "page_no": metadata.get("page_no"),
                        "section_title": metadata.get("section_title") or "",
                    },
                    metadata_json=metadata,
                )
                session.add(row)
                rows.append(row)
            session.flush()
            db_nodes = []
            for row in rows:
                row.vector_doc_id = row.id
                db_nodes.append(
                    TextNode(
                        id_=row.id,
                        text=row.content,
                        metadata=_vector_metadata({
                            **(row.metadata_json or {}),
                            "chunk_id": row.id,
                            "file_id": file_id,
                            "knowledge_file_id": file_id,
                            "knowledge_base_id": knowledge_base_id,
                            "page_no": row.page_no,
                            "section_title": row.section_title,
                            "chunk_index": row.chunk_index,
                        }),
                    )
                )
            session.flush()
            return db_nodes

    def retrieve_payload(
        self,
        *,
        user_id: str,
        query: str,
        knowledge_base_ids: list[str] | None = None,
        conversation_id: str | None = None,
        top_k: int | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        rag_settings = get_settings().rag
        top_k = self._effective_top_k(
            top_k,
            default=rag_settings.default_retrieve_top_k,
            maximum=rag_settings.max_retrieve_top_k,
        )
        used_ids = knowledge_service.resolve_retrieval_scope(
            user_id=user_id,
            knowledge_base_ids=knowledge_base_ids or [],
            conversation_id=conversation_id,
        )
        if not used_ids:
            return {"query": query, "items": [], "total": 0, "used_knowledge_base_ids": []}

        results_by_id: dict[str, dict[str, Any]] = {}
        for knowledge_base_id in used_ids:
            collection = self._collection(knowledge_base_id)
            if collection.count() <= 0:
                continue
            vector_store = ChromaVectorStore(chroma_collection=collection)
            index = VectorStoreIndex.from_vector_store(vector_store, embed_model=self._embedding_model())
            retriever = index.as_retriever(similarity_top_k=max(rag_settings.initial_retrieval_top_k, top_k))
            for hit in retriever.retrieve(query):
                chunk_id = hit.node.node_id
                chunk = self._get_chunk(chunk_id)
                if not chunk or not self._metadata_matches(chunk["metadata"], metadata_filter or {}):
                    continue
                current = self._result_from_chunk(chunk, hit.score or 0)
                existing = results_by_id.get(chunk_id)
                if existing is None or current["score"] > existing["score"]:
                    results_by_id[chunk_id] = current

        items = sorted(results_by_id.values(), key=lambda item: item["score"], reverse=True)[:top_k]
        self._log_retrieval(
            user_id=user_id,
            conversation_id=conversation_id,
            query=query,
            knowledge_base_ids=used_ids,
            top_k=top_k,
            items=items,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        return {"query": query, "items": items, "total": len(items), "used_knowledge_base_ids": used_ids}

    def _metadata_matches(self, metadata: dict[str, Any], metadata_filter: dict[str, Any]) -> bool:
        for key, expected in metadata_filter.items():
            if metadata.get(key) != expected:
                return False
        return True

    def _get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        with db_session() as session:
            record = session.get(tables.PaperChatKnowledgeChunkRecord, chunk_id)
            return self._chunk_payload(record) if record else None

    def expand_chunk_payload(self, *, user_id: str, chunk_id: str, window: int | None = None) -> dict[str, Any]:
        rag_settings = get_settings().rag
        window = max(
            0,
            min(
                window if window is not None else rag_settings.default_expand_window,
                max(0, rag_settings.max_expand_window),
            ),
        )
        with db_session() as session:
            current = session.get(tables.PaperChatKnowledgeChunkRecord, chunk_id)
            if current is None:
                raise AppError(status_code=404, code="RAG_CHUNK_NOT_FOUND", message="片段不存在")
            file_record = session.get(tables.PaperChatKnowledgeFileRecord, current.knowledge_file_id)
            if file_record is None or file_record.user_id != user_id:
                raise AppError(status_code=404, code="RAG_CHUNK_NOT_FOUND", message="片段不存在")
            records = list(
                session.scalars(
                    select(tables.PaperChatKnowledgeChunkRecord)
                    .where(
                        tables.PaperChatKnowledgeChunkRecord.knowledge_file_id == current.knowledge_file_id,
                        tables.PaperChatKnowledgeChunkRecord.chunk_index >= current.chunk_index - window,
                        tables.PaperChatKnowledgeChunkRecord.chunk_index <= current.chunk_index + window,
                    )
                    .order_by(tables.PaperChatKnowledgeChunkRecord.chunk_index)
                )
            )
            chunks = [self._chunk_payload(record) for record in records]
        return {
            "chunk_id": chunk_id,
            "window": window,
            "chunks": chunks,
            "context": "\n\n".join(chunk["content"] for chunk in chunks),
        }

    def index_file_payload(self, *, user_id: str, file_id: str) -> dict[str, Any]:
        file_payload = knowledge_service._file_payload(knowledge_service._require_file(user_id, file_id))
        job = self.create_index_job(user_id=user_id, file_id=file_id, metadata={"trigger": "manual"})
        knowledge_service.repository.update_file(file_id, parser_status="pending", index_status="queued", error_message="")
        return {
            "file_id": file_payload["id"],
            "knowledge_base_id": file_payload["knowledge_base_id"],
            "status": "queued",
            "chunk_count": file_payload["chunk_count"],
            "indexed_at": None,
            "job": job,
            "metadata": {"indexer": "llamaindex", "message": "索引任务已进入队列。"},
        }

    def index_status_payload(self, *, user_id: str, file_id: str) -> dict[str, Any]:
        file_record = knowledge_service._require_file(user_id, file_id)
        file_payload = knowledge_service._file_payload(file_record)
        return {"file": file_payload, "job": self._latest_job(file_id)}

    def answer_payload(
        self,
        *,
        user_id: str,
        query: str,
        knowledge_base_ids: list[str] | None = None,
        conversation_id: str | None = None,
        top_k: int | None = None,
        agentic: bool = True,
    ) -> dict[str, Any]:
        rag_settings = get_settings().rag
        top_k = self._effective_top_k(
            top_k,
            default=rag_settings.default_answer_top_k,
            maximum=rag_settings.max_answer_top_k,
        )
        trace: dict[str, list[Any]] = {"queries": [], "tool_calls": [], "self_evaluations": [], "iterations": []}
        llm = self._llm()
        pending_queries = self._plan_queries(llm, query) if agentic else [query]
        evidence: dict[str, dict[str, Any]] = {}
        used_ids: list[str] = []
        agent_iterations = max(1, rag_settings.max_agent_iterations) if agentic else 1
        max_planned_queries = max(1, rag_settings.max_planned_queries)

        for iteration in range(agent_iterations):
            iteration_queries = list(dict.fromkeys(pending_queries or [query]))[:max_planned_queries]
            trace["queries"].extend(iteration_queries)
            iteration_items = []
            for planned_query in iteration_queries:
                retrieved = self.retrieve_payload(
                    user_id=user_id,
                    query=planned_query,
                    knowledge_base_ids=knowledge_base_ids,
                    conversation_id=conversation_id,
                    top_k=max(top_k, rag_settings.default_answer_top_k),
                )
                used_ids = retrieved["used_knowledge_base_ids"]
                trace["tool_calls"].append(
                    {"tool": "rag.retrieve", "query": planned_query, "result_count": retrieved["total"]}
                )
                for item in retrieved["items"]:
                    evidence[item["chunk_id"]] = item
                    iteration_items.append(item)
            expanded = self._expand_evidence(user_id=user_id, items=list(evidence.values())[:top_k])
            evaluation = self._evaluate_evidence(llm, query=query, evidence=expanded) if agentic else {"sufficient": True}
            trace["self_evaluations"].append(evaluation)
            trace["iterations"].append(
                {
                    "index": iteration + 1,
                    "queries": iteration_queries,
                    "evidence_count": len(evidence),
                    "sufficient": bool(evaluation.get("sufficient")),
                }
            )
            if evaluation.get("sufficient") or not agentic:
                break
            pending_queries = [str(item) for item in evaluation.get("next_queries", []) if str(item).strip()]
            if not pending_queries:
                break

        ranked = sorted(evidence.values(), key=lambda item: item["score"], reverse=True)[:top_k]
        expanded_context = self._expand_evidence(user_id=user_id, items=ranked)
        answer = self._synthesize_answer(llm, query=query, evidence=expanded_context)
        citations = [self._citation_from_result(item) for item in ranked]
        return {
            "answer": answer,
            "citations": citations,
            "trace": trace,
            "used_knowledge_base_ids": used_ids,
        }

    def _plan_queries(self, llm: OpenAI, query: str) -> list[str]:
        max_queries = max(1, get_settings().rag.max_planned_queries)
        prompt = (
            "你是 RAG 查询规划器。请为用户问题生成 2-4 个检索 query，覆盖中文原意、英文术语和关键概念拆分。"
            "只返回 JSON 数组字符串。\n\n用户问题："
            f"{query}"
        )
        text = llm.complete(prompt).text.strip()
        parsed = _json_loads(text, [query])
        if not isinstance(parsed, list):
            return [query]
        queries = [str(item).strip() for item in parsed if str(item).strip()]
        return list(dict.fromkeys([query, *queries]))[:max_queries]

    def _evaluate_evidence(self, llm: OpenAI, *, query: str, evidence: str) -> dict[str, Any]:
        limit = max(1, get_settings().rag.evaluator_context_char_limit)
        prompt = (
            "你是 RAG 自评器。判断证据是否足够回答问题。"
            "返回 JSON：{\"sufficient\": true/false, \"reason\": \"...\", \"next_queries\": [\"...\"]}。"
            "如果证据不足，给出 1-3 个新的检索 query。\n\n"
            f"问题：{query}\n\n证据：\n{evidence[:limit]}"
        )
        parsed = _json_loads(llm.complete(prompt).text.strip(), {})
        if isinstance(parsed, dict):
            return parsed
        return {"sufficient": bool(evidence.strip()), "reason": "fallback", "next_queries": []}

    def _synthesize_answer(self, llm: OpenAI, *, query: str, evidence: str) -> str:
        if not evidence.strip():
            return "当前知识库证据不足，无法基于已索引资料回答这个问题。"
        limit = max(1, get_settings().rag.synthesis_context_char_limit)
        prompt = (
            "你是专业论文知识库问答助手。只能基于给定证据回答，不要编造。"
            "如果证据不足，请明确说明不足。回答用中文，尽量结构化。\n\n"
            f"问题：{query}\n\n证据：\n{evidence[:limit]}"
        )
        return llm.complete(prompt).text.strip()

    def _expand_evidence(self, *, user_id: str, items: list[dict[str, Any]]) -> str:
        window = get_settings().rag.default_expand_window
        blocks = []
        for index, item in enumerate(items, start=1):
            expanded = self.expand_chunk_payload(user_id=user_id, chunk_id=item["chunk_id"], window=window)
            source = item["source"]
            metadata = item["metadata"]
            label = f"[{index}] {source.get('filename')} p.{metadata.get('page_no') or '-'} {metadata.get('section_title') or ''}"
            blocks.append(f"{label}\n{expanded['context']}")
        return "\n\n---\n\n".join(blocks)

    def _citation_from_result(self, item: dict[str, Any]) -> dict[str, Any]:
        metadata = item["metadata"]
        source = item["source"]
        return {
            "file_id": source["file_id"],
            "chunk_id": item["chunk_id"],
            "filename": source["filename"],
            "page_no": metadata.get("page_no"),
            "section_title": metadata.get("section_title") or "",
            "score": item["score"],
            "snippet": item["text"][: max(1, get_settings().rag.citation_snippet_chars)],
        }

    def _log_retrieval(
        self,
        *,
        user_id: str,
        conversation_id: str | None,
        query: str,
        knowledge_base_ids: list[str],
        top_k: int,
        items: list[dict[str, Any]],
        latency_ms: int,
    ) -> None:
        with db_session() as session:
            session.add(
                tables.PaperChatRagRetrievalLogRecord(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    query_text=query,
                    knowledge_base_ids_json=knowledge_base_ids,
                    top_k=top_k,
                    result_count=len(items),
                    latency_ms=latency_ms,
                    results_json=items,
                )
            )


rag_service = RagService()
