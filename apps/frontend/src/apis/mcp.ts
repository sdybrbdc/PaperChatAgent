import type {
  McpServiceCreatePayload,
  McpServiceDTO,
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
    description: String(data.description ?? ''),
    inputSchema: record(data.input_schema ?? data.inputSchema),
    enabled: Boolean(data.enabled ?? true),
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
    url: String(data.url ?? ''),
    status: String(data.status ?? 'enabled'),
    lastHealthStatus: String(data.last_health_status ?? data.lastHealthStatus ?? 'unknown'),
    lastHealthMessage: String(data.last_health_message ?? data.lastHealthMessage ?? ''),
    toolCount: Number(data.tool_count ?? data.toolCount ?? 0),
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

export async function getMcpTools() {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/mcp/tools')
  return list(response.data.data).map(normalizeTool)
}

export async function testMcpService(serviceId: string) {
  const response = await apiClient.post<ApiEnvelope<unknown>>(`/mcp/services/${serviceId}/test`)
  return normalizeTestResult(response.data.data)
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
