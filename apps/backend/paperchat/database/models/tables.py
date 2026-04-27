from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from paperchat.database.sql import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PaperChatUserRecord(Base):
    __tablename__ = "paperchat_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    avatar_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatUserSessionRecord(Base):
    __tablename__ = "paperchat_user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatConversationRecord(Base):
    __tablename__ = "paperchat_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    title_finalized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_message_preview: Mapped[str] = mapped_column(Text, nullable=False, default="")
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatMessageRecord(Base):
    __tablename__ = "paperchat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_conversations.id"), nullable=False, index=True
    )
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False, default="chat")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    citations_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)


class PaperChatConversationGuidanceSnapshotRecord(Base):
    __tablename__ = "paperchat_conversation_guidance_snapshots"

    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_conversations.id"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="casual_chat")
    headline: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sections_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    draft_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatConversationRealtimeEventRecord(Base):
    __tablename__ = "paperchat_conversation_realtime_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_conversations.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)


class PaperChatConversationMemoryRecord(Base):
    __tablename__ = "paperchat_conversation_memories"

    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_conversations.id"), primary_key=True
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    key_points_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    user_preferences_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    open_questions_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    compressed_message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatUserMemoryRecord(Base):
    __tablename__ = "paperchat_user_memories"
    __table_args__ = (
        UniqueConstraint("user_id", "memory_fingerprint", name="uk_paperchat_user_memory_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False, default="preference")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    memory_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    source_conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("paperchat_conversations.id"), nullable=True, index=True
    )
    source_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatAgentWorkflowRecord(Base):
    __tablename__ = "paperchat_agent_workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="builtin")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    definition_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatAgentNodeConfigOverrideRecord(Base):
    __tablename__ = "paperchat_agent_node_config_overrides"
    __table_args__ = (
        UniqueConstraint("user_id", "workflow_id", "node_id", name="uk_paperchat_agent_node_config_user_workflow_node"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_agent_workflows.id"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    executor_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    fallback_executor_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    model_slot: Mapped[str] = mapped_column(String(64), nullable=False, default="conversation_model")
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatResearchTaskRecord(Base):
    __tablename__ = "paperchat_research_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("paperchat_conversations.id"), nullable=True, index=True
    )
    workflow_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_agent_workflows.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    current_node: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    failed_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PaperChatWorkflowRunRecord(Base):
    __tablename__ = "paperchat_workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_research_tasks.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("paperchat_conversations.id"), nullable=True, index=True
    )
    workflow_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_agent_workflows.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    current_node: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    input_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    checkpoint_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatWorkflowNodeRunRecord(Base):
    __tablename__ = "paperchat_workflow_node_runs"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "node_id", name="uk_paperchat_workflow_node_run"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workflow_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_workflow_runs.id"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parent_node_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PaperChatTaskArtifactRecord(Base):
    __tablename__ = "paperchat_task_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_research_tasks.id"), nullable=False, index=True)
    workflow_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_workflow_runs.id"), nullable=False, index=True
    )
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class PaperChatKnowledgeBaseRecord(Base):
    __tablename__ = "paperchat_knowledge_bases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    indexed_file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatKnowledgeFileRecord(Base):
    __tablename__ = "paperchat_knowledge_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    knowledge_base_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_knowledge_bases.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="upload")
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    object_key: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    parsed_text_object_key: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    parser_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    index_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatKnowledgeChunkRecord(Base):
    __tablename__ = "paperchat_knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("knowledge_file_id", "chunk_index", name="uk_paperchat_knowledge_chunk_file_index"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    knowledge_base_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_knowledge_bases.id"), nullable=False, index=True
    )
    knowledge_file_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_knowledge_files.id"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    page_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    vector_collection: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    vector_doc_id: Mapped[str] = mapped_column(String(255), nullable=False, default="", index=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locator_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class PaperChatConversationKnowledgeBindingRecord(Base):
    __tablename__ = "paperchat_conversation_knowledge_bindings"
    __table_args__ = (
        UniqueConstraint("conversation_id", "knowledge_base_id", name="uk_paperchat_conversation_knowledge_binding"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_conversations.id"), nullable=False, index=True
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_knowledge_bases.id"), nullable=False, index=True
    )
    binding_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class PaperChatRagIndexJobRecord(Base):
    __tablename__ = "paperchat_rag_index_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    knowledge_file_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("paperchat_knowledge_files.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parser_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    embedding_route_key: Mapped[str] = mapped_column(String(64), nullable=False, default="embedding")
    error_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatRagRetrievalLogRecord(Base):
    __tablename__ = "paperchat_rag_retrieval_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("paperchat_conversations.id"), nullable=True, index=True
    )
    message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    knowledge_base_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    results_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)


class PaperChatCitationEvidenceRecord(Base):
    __tablename__ = "paperchat_citation_evidences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_messages.id"), nullable=False, index=True)
    knowledge_file_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("paperchat_knowledge_files.id"), nullable=True, index=True
    )
    knowledge_chunk_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("paperchat_knowledge_chunks.id"), nullable=True, index=True
    )
    retrieval_log_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    locator_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class PaperChatMcpServerRecord(Base):
    __tablename__ = "paperchat_mcp_servers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    transport_type: Mapped[str] = mapped_column(String(32), nullable=False, default="stdio")
    command: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    args_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    endpoint_url: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    headers_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    env_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    secret_config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="disabled", index=True)
    last_health_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatMcpToolRecord(Base):
    __tablename__ = "paperchat_mcp_tools"
    __table_args__ = (
        UniqueConstraint("server_id", "tool_name", name="uk_paperchat_mcp_tool_server_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    server_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_mcp_servers.id"), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    input_schema_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatSkillConfigRecord(Base):
    __tablename__ = "paperchat_skill_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    source_uri: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    entrypoint: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="disabled", index=True)
    manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    input_schema_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_schema_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatSkillVersionRecord(Base):
    __tablename__ = "paperchat_skill_versions"
    __table_args__ = (
        UniqueConstraint("skill_id", "version", name="uk_paperchat_skill_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    skill_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_skill_configs.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class PaperChatModelProviderRecord(Base):
    __tablename__ = "paperchat_model_providers"
    __table_args__ = (
        UniqueConstraint("user_id", "provider_key", name="uk_paperchat_model_provider_user_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    provider_key: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    api_key_secret_ref: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatModelRouteConfigRecord(Base):
    __tablename__ = "paperchat_model_route_configs"
    __table_args__ = (
        UniqueConstraint("user_id", "route_key", name="uk_paperchat_model_route_user_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    route_key: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_model_providers.id"), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class PaperChatModelInvocationLogRecord(Base):
    __tablename__ = "paperchat_model_invocation_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    workflow_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    route_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider_key: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="success", index=True)
    error_code: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)


class PaperChatToolInvocationLogRecord(Base):
    __tablename__ = "paperchat_tool_invocation_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    capability_id: Mapped[str] = mapped_column(String(255), nullable=False)
    capability_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    input_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="success", index=True)
    error_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)


class PaperChatTaskEventRecord(Base):
    __tablename__ = "paperchat_task_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_research_tasks.id"), nullable=False, index=True)
    workflow_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)


class PaperChatDashboardMetricSnapshotRecord(Base):
    __tablename__ = "paperchat_dashboard_metric_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("paperchat_users.id"), nullable=False, index=True)
    metric_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    dimension_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, index=True)
