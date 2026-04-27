export interface McpServiceDTO {
  id: string
  name: string
  description: string
  transportType: string
  command: string
  args: string[]
  url: string
  status: string
  lastHealthStatus: string
  lastHealthMessage: string
  toolCount: number
  createdAt: string | null
  updatedAt: string | null
  tools?: McpToolDTO[]
}

export interface McpToolDTO {
  id: string
  serviceId: string
  serviceName: string
  toolName: string
  description: string
  inputSchema: Record<string, unknown>
  enabled: boolean
  updatedAt: string | null
}

export interface McpTestResultDTO {
  ok: boolean
  status: string
  message: string
  latencyMs: number
  tools: McpToolDTO[]
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
