export interface KnowledgeFileDTO {
  id: string
  title: string
  subtitle: string
}

export interface KnowledgeBaseDTO {
  id: string
  title: string
  description: string
  files: KnowledgeFileDTO[]
}

export interface KnowledgeSideCardDTO {
  title: string
  lines: string[]
}
