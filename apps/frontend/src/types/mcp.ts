export interface McpServiceDTO {
  id: string
  name: string
  description: string
  transportType: string
  command: string
  args: string[]
  endpointUrl: string
  url: string
  headers: Record<string, string>
  envKeys: string[]
  hasSecretConfig: boolean
  status: string
  lastHealthStatus: string
  lastHealthMessage: string
  toolCount: number
  lastCheckedAt: string | null
  createdAt: string | null
  updatedAt: string | null
  tools?: McpToolDTO[]
}

export interface McpToolDTO {
  id: string
  serviceId: string
  serviceName: string
  toolName: string
  displayName: string
  description: string
  inputSchema: Record<string, unknown>
  status: string
  enabled: boolean
  lastSeenAt: string | null
  updatedAt: string | null
}

export interface McpTestResultDTO {
  ok: boolean
  status: string
  message: string
  latencyMs: number
  details: Record<string, unknown>
  tools: McpToolDTO[]
}

export interface McpToolCallResultDTO {
  service: McpServiceDTO
  toolName: string
  arguments: Record<string, unknown>
  result: Record<string, unknown>
}

export interface McpServiceCreatePayload {
  name: string
  description?: string
  transportType?: string
  command?: string
  args?: string[]
  endpointUrl?: string
  headers?: Record<string, string>
  env?: Record<string, string>
  status?: string
}

export interface McpServiceUpdatePayload {
  name?: string
  description?: string
  transportType?: string
  command?: string
  args?: string[]
  endpointUrl?: string
  headers?: Record<string, string>
  env?: Record<string, string>
  status?: string
}

export interface McpImportJsonPayload {
  config: unknown
  overwriteExisting?: boolean
  refreshTools?: boolean
  status?: string
}

export interface McpImportJsonResultDTO {
  created: number
  updated: number
  refreshed: number
  refreshErrors: Record<string, unknown>[]
  total: number
  items: McpServiceDTO[]
}
