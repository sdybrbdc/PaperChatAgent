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
