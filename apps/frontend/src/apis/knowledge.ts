import type {
  KnowledgeBaseCreatePayload,
  KnowledgeBaseDTO,
  KnowledgeBindingDTO,
  KnowledgeBindingPayload,
  KnowledgeFileDTO,
  RagAnswerDTO,
  RagCitationDTO,
  RagChunkDTO,
  RagIndexFileDTO,
  RagIndexJobDTO,
  RagIndexStatusDTO,
  RagRetrieveDTO,
  RagRetrievePayload,
  RagSourceDTO,
} from '../types/knowledge'
import { apiClient } from '../utils/http'

interface ApiEnvelope<T> {
  code?: string
  message?: string
  data: T
  request_id?: string
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function items(value: unknown): unknown[] {
  if (Array.isArray(value)) return value
  const data = record(value)
  return Array.isArray(data.items) ? data.items : []
}

function normalizeFile(value: unknown): KnowledgeFileDTO {
  const data = record(value)
  return {
    id: String(data.id ?? ''),
    knowledgeBaseId: String(data.knowledge_base_id ?? data.knowledgeBaseId ?? ''),
    filename: String(data.filename ?? data.name ?? ''),
    originalFilename: String(data.original_filename ?? data.originalFilename ?? data.filename ?? ''),
    mimeType: String(data.mime_type ?? data.mimeType ?? ''),
    sizeBytes: Number(data.size_bytes ?? data.sizeBytes ?? 0),
    parserStatus: String(data.parser_status ?? data.parserStatus ?? 'pending'),
    indexStatus: String(data.index_status ?? data.indexStatus ?? 'pending'),
    chunkCount: Number(data.chunk_count ?? data.chunkCount ?? 0),
    sourceType: String(data.source_type ?? data.sourceType ?? 'upload'),
    sourceUri: String(data.source_uri ?? data.sourceUri ?? ''),
    objectKey: String(data.object_key ?? data.objectKey ?? ''),
    errorMessage: String(data.error_message ?? data.errorMessage ?? data.error_text ?? ''),
    createdAt: (data.created_at as string | null | undefined) ?? (data.createdAt as string | null | undefined) ?? null,
    updatedAt: (data.updated_at as string | null | undefined) ?? (data.updatedAt as string | null | undefined) ?? null,
  }
}

function normalizeBase(value: unknown): KnowledgeBaseDTO {
  const data = record(value)
  return {
    id: String(data.id ?? ''),
    name: String(data.name ?? ''),
    description: String(data.description ?? ''),
    status: String(data.status ?? 'active'),
    fileCount: Number(data.file_count ?? data.fileCount ?? 0),
    indexedFileCount: Number(data.indexed_file_count ?? data.indexedFileCount ?? 0),
    createdAt: (data.created_at as string | null | undefined) ?? (data.createdAt as string | null | undefined) ?? null,
    updatedAt: (data.updated_at as string | null | undefined) ?? (data.updatedAt as string | null | undefined) ?? null,
    recentFiles: Array.isArray(data.recent_files) ? data.recent_files.map(normalizeFile) : undefined,
  }
}

function normalizeBinding(value: unknown): KnowledgeBindingDTO {
  const data = record(value)
  const base = record(data.knowledge_base)
  return {
    id: String(data.id ?? ''),
    conversationId: String(data.conversation_id ?? data.conversationId ?? data.session_id ?? ''),
    knowledgeBaseId: String(data.knowledge_base_id ?? data.knowledgeBaseId ?? base.id ?? ''),
    knowledgeBaseName: String(data.knowledge_base_name ?? data.knowledgeBaseName ?? base.name ?? ''),
    bindingType: String(data.binding_type ?? data.bindingType ?? 'manual'),
    createdAt: (data.created_at as string | null | undefined) ?? (data.createdAt as string | null | undefined) ?? null,
  }
}

function normalizeRagSource(value: unknown): RagSourceDTO {
  const data = record(value)
  return {
    fileId: String(data.file_id ?? data.fileId ?? ''),
    knowledgeBaseId: String(data.knowledge_base_id ?? data.knowledgeBaseId ?? ''),
    title: String(data.title ?? ''),
    filename: String(data.filename ?? ''),
    sourceType: String(data.source_type ?? data.sourceType ?? ''),
    sourceUri: String(data.source_uri ?? data.sourceUri ?? ''),
    metadata: record(data.metadata),
  }
}

function normalizeRagChunk(value: unknown): RagChunkDTO {
  const data = record(value)
  return {
    id: String(data.id ?? ''),
    chunkId: String(data.chunk_id ?? data.chunkId ?? data.id ?? ''),
    text: String(data.text ?? ''),
    score: Number(data.score ?? 0),
    source: normalizeRagSource(data.source),
    metadata: record(data.metadata),
  }
}

function normalizeRagRetrieve(value: unknown): RagRetrieveDTO {
  const data = record(value)
  return {
    query: String(data.query ?? ''),
    items: items(data).map(normalizeRagChunk),
    total: Number(data.total ?? 0),
    usedKnowledgeBaseIds: Array.isArray(data.used_knowledge_base_ids)
      ? data.used_knowledge_base_ids.map(String)
      : Array.isArray(data.usedKnowledgeBaseIds)
        ? data.usedKnowledgeBaseIds.map(String)
        : [],
  }
}

function normalizeRagIndexJob(value: unknown): RagIndexJobDTO {
  const data = record(value)
  return {
    id: String(data.id ?? ''),
    status: String(data.status ?? 'queued'),
    stage: String(data.stage ?? 'queued'),
    progress: Number(data.progress ?? 0),
    errorText: String(data.error_text ?? data.errorText ?? ''),
  }
}

function normalizeRagIndexFile(value: unknown): RagIndexFileDTO {
  const data = record(value)
  const job = record(data.job)
  return {
    fileId: String(data.file_id ?? data.fileId ?? ''),
    knowledgeBaseId: String(data.knowledge_base_id ?? data.knowledgeBaseId ?? ''),
    status: String(data.status ?? 'pending'),
    chunkCount: Number(data.chunk_count ?? data.chunkCount ?? 0),
    indexedAt: (data.indexed_at as string | null | undefined) ?? (data.indexedAt as string | null | undefined) ?? null,
    metadata: record(data.metadata),
    job: job.id ? normalizeRagIndexJob(job) : undefined,
  }
}

function normalizeRagCitation(value: unknown): RagCitationDTO {
  const data = record(value)
  return {
    fileId: String(data.file_id ?? data.fileId ?? ''),
    chunkId: String(data.chunk_id ?? data.chunkId ?? ''),
    filename: String(data.filename ?? ''),
    pageNo:
      data.page_no === null || data.pageNo === null
        ? null
        : Number(data.page_no ?? data.pageNo ?? 0) || null,
    sectionTitle: String(data.section_title ?? data.sectionTitle ?? ''),
    score: Number(data.score ?? 0),
    snippet: String(data.snippet ?? ''),
  }
}

function normalizeRagAnswer(value: unknown): RagAnswerDTO {
  const data = record(value)
  return {
    answer: String(data.answer ?? ''),
    citations: Array.isArray(data.citations) ? data.citations.map(normalizeRagCitation) : [],
    trace: record(data.trace),
    usedKnowledgeBaseIds: Array.isArray(data.used_knowledge_base_ids)
      ? data.used_knowledge_base_ids.map(String)
      : Array.isArray(data.usedKnowledgeBaseIds)
        ? data.usedKnowledgeBaseIds.map(String)
        : [],
  }
}

export async function getKnowledgeBases(params?: { status?: string; keyword?: string }) {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/knowledge/bases', { params })
  return items(response.data.data).map(normalizeBase)
}

export async function createKnowledgeBase(payload: KnowledgeBaseCreatePayload) {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/knowledge/bases', payload)
  return normalizeBase(response.data.data)
}

export async function getKnowledgeBase(baseId: string) {
  const response = await apiClient.get<ApiEnvelope<unknown>>(`/knowledge/bases/${baseId}`)
  return normalizeBase(response.data.data)
}

export async function getKnowledgeFiles(baseId: string) {
  const response = await apiClient.get<ApiEnvelope<unknown>>(`/knowledge/bases/${baseId}/files`)
  return items(response.data.data).map(normalizeFile)
}

export async function uploadKnowledgeFile(baseId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post<ApiEnvelope<unknown>>(`/knowledge/bases/${baseId}/files/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  const data = record(response.data.data)
  return normalizeFile(data.id ? data : response.data.data)
}

export async function importArxivFile(baseId: string, arxivId: string) {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/knowledge/import/arxiv', {
    knowledge_base_id: baseId,
    arxiv_id: arxivId,
  })
  return normalizeFile(response.data.data)
}

export async function bindKnowledgeBase(payload: KnowledgeBindingPayload) {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/knowledge/conversation-bindings', {
    conversation_id: payload.conversationId,
    knowledge_base_id: payload.knowledgeBaseId,
    binding_type: payload.bindingType ?? 'manual',
  })
  return normalizeBinding(response.data.data)
}

export async function getConversationKnowledgeBindings(conversationId: string) {
  const response = await apiClient.get<ApiEnvelope<unknown>>(`/knowledge/conversations/${conversationId}/bindings`)
  return items(response.data.data).map(normalizeBinding)
}

export async function retrieveKnowledge(payload: RagRetrievePayload) {
  const requestPayload: Record<string, unknown> = {
    query: payload.query,
    knowledge_base_ids: payload.knowledgeBaseIds ?? [],
    conversation_id: payload.conversationId,
    metadata_filter: payload.metadataFilter ?? {},
  }
  if (payload.topK !== undefined) requestPayload.top_k = payload.topK
  const response = await apiClient.post<ApiEnvelope<unknown>>('/knowledge/rag/retrieve', requestPayload)
  return normalizeRagRetrieve(response.data.data)
}

export async function indexKnowledgeFile(fileId: string) {
  const response = await apiClient.post<ApiEnvelope<unknown>>(`/knowledge/rag/files/${fileId}/index`)
  return normalizeRagIndexFile(response.data.data)
}

export async function getKnowledgeFileIndexStatus(fileId: string): Promise<RagIndexStatusDTO> {
  const response = await apiClient.get<ApiEnvelope<unknown>>(`/knowledge/rag/files/${fileId}/index-status`)
  const data = record(response.data.data)
  return {
    file: normalizeFile(data.file),
    job: data.job ? normalizeRagIndexJob(data.job) : null,
  }
}

export async function answerKnowledge(payload: RagRetrievePayload & { agentic?: boolean }) {
  const requestPayload: Record<string, unknown> = {
    query: payload.query,
    knowledge_base_ids: payload.knowledgeBaseIds ?? [],
    conversation_id: payload.conversationId,
    agentic: payload.agentic ?? true,
  }
  if (payload.topK !== undefined) requestPayload.top_k = payload.topK
  const response = await apiClient.post<ApiEnvelope<unknown>>('/knowledge/rag/answer', requestPayload)
  return normalizeRagAnswer(response.data.data)
}
