from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from paperchat.services.knowledge import knowledge_service


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RagService:
    def retrieve_payload(
        self,
        *,
        user_id: str,
        query: str,
        knowledge_base_ids: list[str] | None = None,
        conversation_id: str | None = None,
        top_k: int = 8,
        metadata_filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        used_ids = knowledge_service.resolve_retrieval_scope(
            user_id=user_id,
            knowledge_base_ids=knowledge_base_ids or [],
            conversation_id=conversation_id,
        )
        if not used_ids:
            return {
                "query": query,
                "items": [],
                "total": 0,
                "used_knowledge_base_ids": [],
            }

        files = knowledge_service.list_files_for_retrieval(user_id, used_ids)
        metadata_filter = metadata_filter or {}
        candidates = [
            item
            for item in files
            if item["status"] in {"pending", "indexed"} and self._metadata_matches(item["metadata"], metadata_filter)
        ]

        query_terms = {part.lower() for part in query.split() if part.strip()}
        results = []
        for item in candidates:
            haystack = " ".join(
                [
                    item["title"],
                    item["filename"],
                    str(item["metadata"].get("abstract") or ""),
                    str(item["metadata"].get("arxiv_id") or ""),
                ]
            ).lower()
            score = 0.1
            if query_terms:
                matched = sum(1 for term in query_terms if term in haystack)
                score = matched / len(query_terms) if matched else 0.1
            if score <= 0:
                continue
            results.append(
                {
                    "id": f"{item['id']}:metadata",
                    "text": self._build_preview_text(item),
                    "score": round(float(score), 4),
                    "source": {
                        "file_id": item["id"],
                        "knowledge_base_id": item["knowledge_base_id"],
                        "title": item["title"],
                        "filename": item["filename"],
                        "source_type": item["source_type"],
                        "source_uri": item["source_uri"],
                        "metadata": item["metadata"],
                    },
                    "metadata": {
                        "placeholder": True,
                        "retrieval_mode": "metadata",
                        "file_status": item["status"],
                    },
                }
            )

        results.sort(key=lambda item: item["score"], reverse=True)
        results = results[: max(1, min(top_k, 50))]
        return {
            "query": query,
            "items": results,
            "total": len(results),
            "used_knowledge_base_ids": used_ids,
        }

    def index_file_payload(self, *, user_id: str, file_id: str) -> dict[str, Any]:
        file_payload = knowledge_service.mark_file_indexed(
            user_id,
            file_id,
            chunk_count=1,
            metadata={
                "indexer": "placeholder",
                "indexed_at": utcnow().isoformat(),
            },
        )
        return {
            "file_id": file_payload["id"],
            "knowledge_base_id": file_payload["knowledge_base_id"],
            "status": file_payload["status"],
            "chunk_count": file_payload["chunk_count"],
            "indexed_at": datetime.fromisoformat(file_payload["updated_at"]).isoformat(),
            "metadata": {
                "placeholder": True,
                "message": "文件元数据已标记为可检索，正文向量索引等待主线程接入。",
            },
        }

    @staticmethod
    def _metadata_matches(metadata: dict[str, Any], metadata_filter: dict[str, Any]) -> bool:
        for key, expected in metadata_filter.items():
            if metadata.get(key) != expected:
                return False
        return True

    @staticmethod
    def _build_preview_text(file_payload: dict[str, Any]) -> str:
        abstract = str(file_payload["metadata"].get("abstract") or "").strip()
        if abstract:
            return abstract[:800]
        title = file_payload["title"] or file_payload["filename"]
        source_type = file_payload["source_type"]
        if source_type == "arxiv":
            return f"{title} 的 arXiv 元数据占位结果。"
        if source_type == "upload":
            return f"{title} 的上传文件元数据占位结果。"
        return f"{title} 的知识文件元数据占位结果。"


rag_service = RagService()
