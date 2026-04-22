from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, File, Request, UploadFile
from pydantic import BaseModel, Field

from paperchat.api.responses import APIResponse, ok
from paperchat.auth import get_current_user
from paperchat.database.dao import memory_store
from paperchat.services.knowledge import fetch_arxiv_entry
from paperchat.services.storage import storage_service


router = APIRouter(prefix="/knowledge", tags=["Knowledge"])


class ImportArxivRequest(BaseModel):
    keyword: str = Field(min_length=1)
    arxiv_id: str | None = None


class AttachKnowledgeRequest(BaseModel):
    workspace_id: str | None = None
    task_id: str | None = None
    knowledge_file_ids: list[str] = Field(default_factory=list)


@router.get("", response_model=APIResponse)
async def get_knowledge_overview(request: Request, user=Depends(get_current_user)):
    files = memory_store.list_knowledge_files(user.id)
    global_files = [memory_store.as_knowledge_file_payload(item) for item in files if item.workspace_id is None]
    private_files = [memory_store.as_knowledge_file_payload(item) for item in files if item.workspace_id is not None]
    return ok(
        request,
        data={
            "global": {
                "id": "global-kb",
                "title": "账号级全局知识库",
                "description": "可跨工作区复用的资料集合",
                "files": global_files,
            },
            "private": {
                "id": "workspace-private-kb",
                "title": "工作区私有知识库",
                "description": "当前主题专属资料",
                "files": private_files,
            },
            "rail": [
                {
                    "title": "知识库状态",
                    "lines": [
                        f"全局资料数：{len(global_files)}",
                        f"私有资料数：{len(private_files)}",
                        "上传会写入 MySQL 与 MinIO",
                    ],
                }
            ],
        },
    )


@router.post("/files/upload", response_model=APIResponse)
async def upload_knowledge_file(
    request: Request,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    data = await file.read()
    uploaded = storage_service.upload_bytes(
        filename=file.filename or "uploaded-file",
        content_type=file.content_type or "application/octet-stream",
        data=data,
    )
    record = memory_store.create_knowledge_file(
        user_id=user.id,
        source_type="upload_pdf",
        title=file.filename or "uploaded-file",
        source_url=uploaded["url"],
        object_key=uploaded["object_key"],
        parser_status="uploaded",
        index_status="pending",
        metadata_json={"content_type": file.content_type, "size_bytes": len(data)},
    )
    return ok(
        request,
        data=memory_store.as_knowledge_file_payload(record),
    )


@router.post("/import/arxiv", response_model=APIResponse)
async def import_arxiv(payload: ImportArxivRequest, request: Request, user=Depends(get_current_user)):
    entry = await fetch_arxiv_entry(keyword=payload.keyword, arxiv_id=payload.arxiv_id)
    record = memory_store.create_knowledge_file(
        user_id=user.id,
        source_type="arxiv",
        title=entry["title"],
        source_url=entry["entry_id"],
        parser_status="uploaded",
        index_status="pending",
        metadata_json={
            "summary": entry["summary"],
            "published": entry["published"],
            "authors": entry["authors"],
            "pdf_url": entry["pdf_url"],
        },
    )
    return ok(
        request,
        data=memory_store.as_knowledge_file_payload(record),
    )


@router.post("/attach", response_model=APIResponse)
async def attach_knowledge(payload: AttachKnowledgeRequest, request: Request, user=Depends(get_current_user)):
    return ok(
        request,
        data={
            "workspace_id": payload.workspace_id,
            "task_id": payload.task_id,
            "knowledge_file_ids": payload.knowledge_file_ids,
            "attached": True,
        },
    )
