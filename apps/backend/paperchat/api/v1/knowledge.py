from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile

from paperchat.api.responses import APIResponse, ok
from paperchat.auth import get_current_user
from paperchat.schemas.knowledge import (
    ArxivImportPlaceholderRequest,
    ConversationKnowledgeBindingRequest,
    FileUploadPlaceholderRequest,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
)
from paperchat.schemas.rag import RagRetrieveRequest
from paperchat.services.knowledge import knowledge_service
from paperchat.services.rag import rag_service


router = APIRouter(prefix="/knowledge", tags=["Knowledge"])


class ArxivImportRequest(BaseModel):
    knowledge_base_id: str = Field(min_length=1)
    arxiv_id: str = Field(min_length=1, max_length=64)
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    pdf_url: str = ""
    metadata: dict = Field(default_factory=dict)


class ConversationKnowledgeSingleBindingRequest(BaseModel):
    conversation_id: str = Field(min_length=1)
    knowledge_base_id: str = Field(min_length=1)
    binding_type: str = "manual"


@router.get("", response_model=APIResponse)
async def list_knowledge_bases(
    request: Request,
    include_archived: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=knowledge_service.list_knowledge_bases_payload(
            user.id,
            include_archived=include_archived,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/bases", response_model=APIResponse)
async def list_knowledge_bases_v1(
    request: Request,
    include_archived: bool = Query(default=False),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user=Depends(get_current_user),
):
    payload = knowledge_service.list_knowledge_bases_payload(
        user.id,
        include_archived=include_archived or status == "archived",
        limit=limit,
        offset=offset,
    )
    items = payload.get("items", [])
    if status and status != "archived":
        items = [item for item in items if item.get("status") == status]
    if keyword:
        keyword_lower = keyword.lower()
        items = [
            item
            for item in items
            if keyword_lower in str(item.get("name", "")).lower()
            or keyword_lower in str(item.get("description", "")).lower()
        ]
    return ok(request, data={"items": items, "paging": {**payload.get("paging", {}), "total": len(items)}})


@router.post("", response_model=APIResponse)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=knowledge_service.create_knowledge_base_payload(
            user.id,
            name=payload.name,
            description=payload.description,
            visibility=payload.visibility,
            metadata=payload.metadata,
        ),
    )


@router.post("/bases", response_model=APIResponse)
async def create_knowledge_base_v1(
    payload: KnowledgeBaseCreate,
    request: Request,
    user=Depends(get_current_user),
):
    return await create_knowledge_base(payload=payload, request=request, user=user)


@router.get("/conversations/{conversation_id}/binding", response_model=APIResponse)
async def get_conversation_binding(
    conversation_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(request, data=knowledge_service.get_conversation_binding_payload(user.id, conversation_id))


@router.get("/conversations/{conversation_id}/bindings", response_model=APIResponse)
async def get_conversation_bindings_v1(
    conversation_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    binding = knowledge_service.get_conversation_binding_payload(user.id, conversation_id)
    items = []
    for knowledge_base_id in binding.get("knowledge_base_ids", []):
        try:
            base = knowledge_service.get_knowledge_base_payload(user.id, knowledge_base_id)
        except Exception:
            base = {}
        items.append(
            {
                "id": f"{conversation_id}:{knowledge_base_id}",
                "conversation_id": conversation_id,
                "knowledge_base_id": knowledge_base_id,
                "knowledge_base_name": base.get("name", ""),
                "binding_type": "manual",
                "created_at": binding.get("updated_at"),
            }
        )
    return ok(request, data={"items": items})


@router.put("/conversations/{conversation_id}/binding", response_model=APIResponse)
async def bind_conversation(
    conversation_id: str,
    payload: ConversationKnowledgeBindingRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=knowledge_service.bind_conversation_payload(
            user.id,
            conversation_id,
            knowledge_base_ids=payload.knowledge_base_ids,
        ),
    )


@router.post("/conversation-bindings", response_model=APIResponse)
async def bind_conversation_v1(
    payload: ConversationKnowledgeSingleBindingRequest,
    request: Request,
    user=Depends(get_current_user),
):
    current = knowledge_service.get_conversation_binding_payload(user.id, payload.conversation_id)
    next_ids = list(dict.fromkeys([*current.get("knowledge_base_ids", []), payload.knowledge_base_id]))
    binding = knowledge_service.bind_conversation_payload(
        user.id,
        payload.conversation_id,
        knowledge_base_ids=next_ids,
    )
    base = knowledge_service.get_knowledge_base_payload(user.id, payload.knowledge_base_id)
    return ok(
        request,
        data={
            "id": f"{payload.conversation_id}:{payload.knowledge_base_id}",
            "conversation_id": payload.conversation_id,
            "knowledge_base_id": payload.knowledge_base_id,
            "knowledge_base_name": base.get("name", ""),
            "binding_type": payload.binding_type,
            "created_at": binding.get("updated_at"),
        },
    )


@router.post("/import/arxiv", response_model=APIResponse)
async def import_arxiv_v1(
    payload: ArxivImportRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=knowledge_service.create_arxiv_import_placeholder_payload(
            user.id,
            payload.knowledge_base_id,
            arxiv_id=payload.arxiv_id,
            title=payload.title,
            authors=payload.authors,
            abstract=payload.abstract,
            pdf_url=payload.pdf_url,
            metadata=payload.metadata,
        ),
    )


@router.post("/rag/retrieve", response_model=APIResponse)
async def retrieve(
    payload: RagRetrieveRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=rag_service.retrieve_payload(
            user_id=user.id,
            query=payload.query,
            knowledge_base_ids=payload.knowledge_base_ids,
            conversation_id=payload.conversation_id,
            top_k=payload.top_k,
            metadata_filter=payload.metadata_filter,
        ),
    )


@router.post("/rag/files/{file_id}/index", response_model=APIResponse)
async def index_file(file_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=rag_service.index_file_payload(user_id=user.id, file_id=file_id))


@router.get("/{knowledge_base_id}", response_model=APIResponse)
async def get_knowledge_base(
    knowledge_base_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(request, data=knowledge_service.get_knowledge_base_payload(user.id, knowledge_base_id))


@router.get("/bases/{knowledge_base_id}", response_model=APIResponse)
async def get_knowledge_base_v1(
    knowledge_base_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    return await get_knowledge_base(knowledge_base_id=knowledge_base_id, request=request, user=user)


@router.patch("/{knowledge_base_id}", response_model=APIResponse)
async def update_knowledge_base(
    knowledge_base_id: str,
    payload: KnowledgeBaseUpdate,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=knowledge_service.update_knowledge_base_payload(
            user.id,
            knowledge_base_id,
            name=payload.name,
            description=payload.description,
            visibility=payload.visibility,
            status=payload.status,
            metadata=payload.metadata,
        ),
    )


@router.patch("/bases/{knowledge_base_id}", response_model=APIResponse)
async def update_knowledge_base_v1(
    knowledge_base_id: str,
    payload: KnowledgeBaseUpdate,
    request: Request,
    user=Depends(get_current_user),
):
    return await update_knowledge_base(knowledge_base_id=knowledge_base_id, payload=payload, request=request, user=user)


@router.get("/{knowledge_base_id}/files", response_model=APIResponse)
async def list_files(
    knowledge_base_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=knowledge_service.list_files_payload(
            user.id,
            knowledge_base_id,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/bases/{knowledge_base_id}/files", response_model=APIResponse)
async def list_files_v1(
    knowledge_base_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user=Depends(get_current_user),
):
    return await list_files(
        knowledge_base_id=knowledge_base_id,
        request=request,
        limit=limit,
        offset=offset,
        user=user,
    )


@router.post("/bases/{knowledge_base_id}/files/upload", response_model=APIResponse)
async def upload_file_v1(
    knowledge_base_id: str,
    request: Request,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    return ok(
        request,
        data=knowledge_service.create_upload_placeholder_payload(
            user.id,
            knowledge_base_id,
            filename=file.filename or "upload.pdf",
            content_type=file.content_type or "application/octet-stream",
            size_bytes=len(content),
            source_uri="",
            title=file.filename or "上传文件",
            metadata={"upload_placeholder": True},
        ),
    )


@router.post("/{knowledge_base_id}/files/upload-placeholder", response_model=APIResponse)
async def create_upload_placeholder(
    knowledge_base_id: str,
    payload: FileUploadPlaceholderRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=knowledge_service.create_upload_placeholder_payload(
            user.id,
            knowledge_base_id,
            filename=payload.filename,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
            source_uri=payload.source_uri,
            title=payload.title,
            metadata=payload.metadata,
        ),
    )


@router.post("/{knowledge_base_id}/files/arxiv-placeholder", response_model=APIResponse)
async def create_arxiv_placeholder(
    knowledge_base_id: str,
    payload: ArxivImportPlaceholderRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=knowledge_service.create_arxiv_import_placeholder_payload(
            user.id,
            knowledge_base_id,
            arxiv_id=payload.arxiv_id,
            title=payload.title,
            authors=payload.authors,
            abstract=payload.abstract,
            pdf_url=payload.pdf_url,
            metadata=payload.metadata,
        ),
    )
