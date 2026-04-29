import type {
  McpImportJsonPayload,
  McpImportJsonResultDTO,
  McpServiceCreatePayload,
  McpServiceDTO,
  McpServiceUpdatePayload,
  McpTestResultDTO,
  McpToolCallResultDTO,
  McpToolDTO,
} from '../types/mcp'
import { apiClient } from '../utils/http'

interface ApiEnvelope<T> {
  data: T
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function list(value: unknown): unknown[] {
  if (Array.isArray(value)) return value
  const data = record(value)
  return Array.isArray(data.items) ? data.items : []
}

function normalizeTool(value: unknown): McpToolDTO {
  const data = record(value)
  return {
    id: String(data.id ?? ''),
    serviceId: String(data.service_id ?? data.serviceId ?? ''),
    serviceName: String(data.service_name ?? data.serviceName ?? ''),
    toolName: String(data.tool_name ?? data.toolName ?? data.name ?? ''),
    displayName: String(data.display_name ?? data.displayName ?? data.tool_name ?? data.toolName ?? data.name ?? ''),
    description: String(data.description ?? ''),
    inputSchema: record(data.input_schema ?? data.inputSchema),
    status: String(data.status ?? (data.enabled === false ? 'disabled' : 'active')),
    enabled: Boolean(data.enabled ?? data.status !== 'disabled'),
    lastSeenAt: (data.last_seen_at as string | null | undefined) ?? (data.lastSeenAt as string | null | undefined) ?? null,
    updatedAt: (data.updated_at as string | null | undefined) ?? (data.updatedAt as string | null | undefined) ?? null,
  }
}

function normalizeService(value: unknown): McpServiceDTO {
  const data = record(value)
  return {
    id: String(data.id ?? ''),
    name: String(data.name ?? ''),
    description: String(data.description ?? ''),
    transportType: String(data.transport_type ?? data.transportType ?? 'stdio'),
    command: String(data.command ?? ''),
    args: Array.isArray(data.args) ? data.args.map(String) : [],
    endpointUrl: String(data.endpoint_url ?? data.endpointUrl ?? data.url ?? ''),
    url: String(data.url ?? ''),
    headers: Object.fromEntries(Object.entries(record(data.headers)).map(([key, value]) => [key, String(value)])),
    envKeys: Array.isArray(data.env_keys) ? data.env_keys.map(String) : Array.isArray(data.envKeys) ? data.envKeys.map(String) : [],
    hasSecretConfig: Boolean(data.has_secret_config ?? data.hasSecretConfig ?? false),
    status: String(data.status ?? 'enabled'),
    lastHealthStatus: String(data.last_health_status ?? data.lastHealthStatus ?? 'unknown'),
    lastHealthMessage: String(data.last_health_message ?? data.lastHealthMessage ?? ''),
    toolCount: Number(data.tool_count ?? data.toolCount ?? 0),
    lastCheckedAt: (data.last_checked_at as string | null | undefined) ?? (data.lastCheckedAt as string | null | undefined) ?? null,
    createdAt: (data.created_at as string | null | undefined) ?? (data.createdAt as string | null | undefined) ?? null,
    updatedAt: (data.updated_at as string | null | undefined) ?? (data.updatedAt as string | null | undefined) ?? null,
    tools: Array.isArray(data.tools) ? data.tools.map(normalizeTool) : undefined,
  }
}

function normalizeTestResult(value: unknown): McpTestResultDTO {
  const data = record(value)
  return {
    ok: Boolean(data.ok ?? data.success ?? false),
    status: String(data.status ?? ''),
    message: String(data.message ?? ''),
    latencyMs: Number(data.latency_ms ?? data.latencyMs ?? 0),
    details: record(data.details),
    tools: list(data.tools).map(normalizeTool),
  }
}

export async function getMcpServices() {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/mcp/services')
  return list(response.data.data).map(normalizeService)
}

export async function createMcpService(payload: McpServiceCreatePayload) {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/mcp/services', {
    name: payload.name,
    description: payload.description ?? '',
    transport_type: payload.transportType ?? 'stdio',
    command: payload.command ?? '',
    args: payload.args ?? [],
    endpoint_url: payload.endpointUrl ?? '',
    headers: payload.headers ?? {},
    env: payload.env ?? {},
    status: payload.status ?? 'disabled',
  })
  return normalizeService(response.data.data)
}

export async function importMcpJson(payload: McpImportJsonPayload): Promise<McpImportJsonResultDTO> {
  const response = await apiClient.post<ApiEnvelope<unknown>>(
    '/mcp/import-json',
    {
      config: payload.config,
      overwrite_existing: payload.overwriteExisting ?? true,
      refresh_tools: payload.refreshTools ?? false,
      status: payload.status ?? 'enabled',
    },
    { timeout: 60000 },
  )
  const data = record(response.data.data)
  return {
    created: Number(data.created ?? 0),
    updated: Number(data.updated ?? 0),
    refreshed: Number(data.refreshed ?? 0),
    refreshErrors: list(data.refresh_errors).map(record),
    total: Number(data.total ?? 0),
    items: list(data).map(normalizeService),
  }
}

export async function getCcSwitchMcpServices() {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/mcp/sources/cc-switch')
  return {
    source: record(record(response.data.data).source),
    items: list(response.data.data).map(normalizeService),
  }
}

export async function syncCcSwitchMcpServices() {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/mcp/sync/cc-switch')
  const data = record(response.data.data)
  return {
    source: record(data.source),
    created: Number(data.created ?? 0),
    updated: Number(data.updated ?? 0),
    refreshed: Number(data.refreshed ?? 0),
    refreshErrors: list(data.refresh_errors).map(record),
    total: Number(data.total ?? 0),
    items: list(data).map(normalizeService),
  }
}

export async function getMcpService(serviceId: string) {
  const response = await apiClient.get<ApiEnvelope<unknown>>(`/mcp/services/${serviceId}`)
  return normalizeService(response.data.data)
}

export async function updateMcpService(serviceId: string, payload: McpServiceUpdatePayload) {
  const response = await apiClient.patch<ApiEnvelope<unknown>>(`/mcp/services/${serviceId}`, {
    name: payload.name,
    description: payload.description,
    transport_type: payload.transportType,
    command: payload.command,
    args: payload.args,
    endpoint_url: payload.endpointUrl,
    headers: payload.headers,
    env: payload.env,
    status: payload.status,
  })
  return normalizeService(response.data.data)
}

export async function getMcpTools() {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/mcp/tools')
  return list(response.data.data).map(normalizeTool)
}

export async function testMcpService(serviceId: string) {
  const response = await apiClient.post<ApiEnvelope<unknown>>(`/mcp/services/${serviceId}/test`, undefined, { timeout: 60000 })
  return normalizeTestResult(response.data.data)
}

export async function refreshMcpTools(serviceId: string) {
  const response = await apiClient.post<ApiEnvelope<unknown>>(`/mcp/services/${serviceId}/refresh-tools`, undefined, { timeout: 60000 })
  const data = record(response.data.data)
  return {
    ok: Boolean(data.ok ?? false),
    refreshed: Boolean(data.refreshed ?? false),
    message: String(data.message ?? ''),
    tools: list(data.tools).map(normalizeTool),
  }
}

export async function callMcpTool(
  serviceId: string,
  toolName: string,
  argumentsPayload: Record<string, unknown>,
): Promise<McpToolCallResultDTO> {
  const response = await apiClient.post<ApiEnvelope<unknown>>(`/mcp/services/${serviceId}/tools/${toolName}/call`, {
    arguments: argumentsPayload,
  })
  const data = record(response.data.data)
  return {
    service: normalizeService(data.service),
    toolName: String(data.tool_name ?? data.toolName ?? toolName),
    arguments: record(data.arguments),
    result: record(data.result),
  }
}
