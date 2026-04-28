export type SkillFileNode = {
  name: string
  path: string
  type: 'file'
  content: string
}

export type SkillFolderNode = {
  name: string
  path: string
  type: 'folder'
  folder: SkillTreeNode[]
}

export type SkillTreeNode = SkillFileNode | SkillFolderNode

export interface SkillDTO {
  id: string
  name: string
  description: string
  sourceType: string
  sourceUri: string
  entrypoint: string
  status: string
  version: string
  manifest: Record<string, unknown>
  inputSchema: Record<string, unknown>
  outputSchema: Record<string, unknown>
  metadata: Record<string, unknown>
  folder: SkillFolderNode | null
  content: string
  contentPreview: string
  contentSource: string
  fileCount: number
  asToolName: string
  triggerPhrases: string[]
  createdAt: string | null
  updatedAt: string | null
}

export interface SkillTestResultDTO {
  ok: boolean
  message: string
  output: unknown
  latencyMs: number
  validation: Record<string, unknown>
}

export interface SkillCreatePayload {
  name: string
  description?: string
  sourceType?: string
  sourceUri?: string
  entrypoint?: string
  status?: string
  content?: string
  manifest?: Record<string, unknown>
  inputSchema?: Record<string, unknown>
  outputSchema?: Record<string, unknown>
  metadata?: Record<string, unknown>
}

export interface SkillUpdatePayload {
  name?: string
  description?: string
  sourceType?: string
  sourceUri?: string
  entrypoint?: string
  status?: string
  content?: string
  manifest?: Record<string, unknown>
  inputSchema?: Record<string, unknown>
  outputSchema?: Record<string, unknown>
  metadata?: Record<string, unknown>
}

export interface SkillImportPayload {
  sourceUri?: string
  status?: string
}

export interface SkillImportResultDTO {
  created: string[]
  skipped: string[]
  failed: Array<{ name: string; path: string; error: string }>
  sourceCount: number
  items: SkillDTO[]
}

export interface SkillFileUpdatePayload {
  path: string
  content: string
}

export interface SkillFileAddPayload {
  path: string
  name: string
  content?: string
}

export interface SkillFileDeletePayload {
  path: string
}
