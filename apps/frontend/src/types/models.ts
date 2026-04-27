export interface ModelProviderDTO {
  id: string
  name: string
  providerType: string
  baseUrl: string
  status: string
  modelCount: number
  createdAt: string | null
  updatedAt: string | null
}

export interface ModelRouteDTO {
  id: string
  routeKey: string
  label: string
  providerId: string
  providerName: string
  modelName: string
  temperature: number
  maxTokens: number
  status: string
  config: Record<string, unknown>
  updatedAt: string | null
}

export interface ModelRouteUpdatePayload {
  providerId: string
  modelName: string
  temperature?: number
  maxTokens?: number
  config?: Record<string, unknown>
}

export interface ModelTestResultDTO {
  ok: boolean
  output: string
  latencyMs: number
  inputTokens: number
  outputTokens: number
  message: string
}

export interface ModelProviderCreatePayload {
  name: string
  providerType?: string
  baseUrl?: string
  apiKeyRef?: string
  status?: string
  config?: Record<string, unknown>
}
