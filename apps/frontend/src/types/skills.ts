export interface SkillDTO {
  id: string
  name: string
  description: string
  sourceType: string
  sourceUri: string
  entrypoint: string
  status: string
  version: string
  inputSchema: Record<string, unknown>
  outputSchema: Record<string, unknown>
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
  manifest?: Record<string, unknown>
  inputSchema?: Record<string, unknown>
  outputSchema?: Record<string, unknown>
  metadata?: Record<string, unknown>
}

export interface SkillImportPayload {
  sourceUri: string
  status?: string
}
