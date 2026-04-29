export interface KnowledgeBaseDTO {
  id: string
  name: string
  description: string
  status: string
  fileCount: number
  indexedFileCount: number
  createdAt: string | null
  updatedAt: string | null
  recentFiles?: KnowledgeFileDTO[]
}

export interface KnowledgeFileDTO {
  id: string
  knowledgeBaseId: string
  filename: string
  originalFilename: string
  mimeType: string
  sizeBytes: number
  parserStatus: string
  indexStatus: string
  chunkCount: number
  sourceType: string
  sourceUri: string
  objectKey: string
  errorMessage: string
  createdAt: string | null
  updatedAt: string | null
}

export interface KnowledgeBindingDTO {
  id: string
  conversationId: string
  knowledgeBaseId: string
  knowledgeBaseName: string
  bindingType: string
  createdAt: string | null
}

export interface KnowledgeBaseCreatePayload {
  name: string
  description: string
}

export interface KnowledgeBindingPayload {
  conversationId: string
  knowledgeBaseId: string
  bindingType?: string
}

export interface RagRetrievePayload {
  query: string
  knowledgeBaseIds?: string[]
  conversationId?: string
  topK?: number
  metadataFilter?: Record<string, unknown>
}

export interface RagSourceDTO {
  fileId: string
  knowledgeBaseId: string
  title: string
  filename: string
  sourceType: string
  sourceUri: string
  metadata: Record<string, unknown>
}

export interface RagChunkDTO {
  id: string
  chunkId: string
  text: string
  score: number
  source: RagSourceDTO
  metadata: Record<string, unknown>
}

export interface RagRetrieveDTO {
  query: string
  items: RagChunkDTO[]
  total: number
  usedKnowledgeBaseIds: string[]
}

export interface RagIndexFileDTO {
  fileId: string
  knowledgeBaseId: string
  status: string
  chunkCount: number
  indexedAt: string | null
  metadata: Record<string, unknown>
  job?: RagIndexJobDTO
}

export interface RagIndexJobDTO {
  id: string
  status: string
  stage: string
  progress: number
  errorText: string
}

export interface RagIndexStatusDTO {
  file: KnowledgeFileDTO
  job: RagIndexJobDTO | null
}

export interface RagCitationDTO {
  fileId: string
  chunkId: string
  filename: string
  pageNo: number | null
  sectionTitle: string
  score: number
  snippet: string
}

export interface RagAnswerDTO {
  answer: string
  citations: RagCitationDTO[]
  trace: Record<string, unknown>
  usedKnowledgeBaseIds: string[]
}
