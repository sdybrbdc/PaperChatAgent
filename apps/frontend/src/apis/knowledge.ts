import type {
  KnowledgeBaseCreatePayload,
  KnowledgeBaseDTO,
  KnowledgeBindingDTO,
  KnowledgeBindingPayload,
  KnowledgeFileDTO,
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
  return normalizeFile(response.data.data)
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
