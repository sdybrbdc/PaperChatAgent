import type {
  ModelProviderCreatePayload,
  ModelProviderDTO,
  ModelRouteDTO,
  ModelRouteUpdatePayload,
  ModelTestResultDTO,
} from '../types/models'
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

function normalizeProvider(value: unknown): ModelProviderDTO {
  const data = record(value)
  return {
    id: String(data.id ?? ''),
    name: String(data.name ?? ''),
    providerKey: String(data.provider_key ?? data.providerKey ?? ''),
    providerType: String(data.provider_type ?? data.providerType ?? ''),
    baseUrl: String(data.base_url ?? data.baseUrl ?? ''),
    apiKeyRef: String(data.api_key_ref ?? data.apiKeyRef ?? ''),
    status: String(data.status ?? 'enabled'),
    modelCount: Number(data.model_count ?? data.modelCount ?? 0),
    config: record(data.config),
    createdAt: (data.created_at as string | null | undefined) ?? (data.createdAt as string | null | undefined) ?? null,
    updatedAt: (data.updated_at as string | null | undefined) ?? (data.updatedAt as string | null | undefined) ?? null,
  }
}

function normalizeRoute(value: unknown): ModelRouteDTO {
  const data = record(value)
  return {
    id: String(data.id ?? data.route_key ?? ''),
    routeKey: String(data.route_key ?? data.routeKey ?? ''),
    label: String(data.label ?? data.route_key ?? ''),
    providerId: String(data.provider_id ?? data.providerId ?? ''),
    providerName: String(data.provider_name ?? data.providerName ?? ''),
    modelName: String(data.model_name ?? data.modelName ?? ''),
    modelType: String(data.model_type ?? data.modelType ?? record(data.config).model_type ?? 'chat'),
    priority: Number(data.priority ?? record(data.config).priority ?? 100),
    isDefault: Boolean(data.is_default ?? data.isDefault ?? record(data.config).is_default ?? false),
    temperature: Number(data.temperature ?? 0),
    maxTokens: Number(data.max_tokens ?? data.maxTokens ?? 0),
    status: String(data.status ?? 'enabled'),
    config: record(data.config),
    updatedAt: (data.updated_at as string | null | undefined) ?? (data.updatedAt as string | null | undefined) ?? null,
  }
}

function normalizeTestResult(value: unknown): ModelTestResultDTO {
  const data = record(value)
  return {
    ok: Boolean(data.ok ?? data.success ?? true),
    output: String(data.output ?? data.text ?? ''),
    latencyMs: Number(data.latency_ms ?? data.latencyMs ?? 0),
    inputTokens: Number(data.input_tokens ?? data.inputTokens ?? 0),
    outputTokens: Number(data.output_tokens ?? data.outputTokens ?? 0),
    message: String(data.message ?? ''),
  }
}

export async function getModelProviders() {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/models/providers')
  return list(response.data.data).map(normalizeProvider)
}

export async function createModelProvider(payload: ModelProviderCreatePayload) {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/models/providers', {
    name: payload.name,
    provider_type: payload.providerType ?? 'openai_compatible',
    base_url: payload.baseUrl ?? '',
    api_key_ref: payload.apiKeyRef ?? '',
    status: payload.status ?? 'active',
    config: payload.config ?? {},
  })
  return normalizeProvider(response.data.data)
}

export async function getModelRoutes() {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/models/routes')
  return list(response.data.data).map(normalizeRoute)
}

export async function updateModelRoute(routeKey: string, payload: ModelRouteUpdatePayload) {
  const response = await apiClient.put<ApiEnvelope<unknown>>(`/models/routes/${routeKey}`, {
    provider_id: payload.providerId,
    model_name: payload.modelName,
    temperature: payload.temperature,
    max_tokens: payload.maxTokens,
    config: payload.config ?? {},
  })
  return normalizeRoute(response.data.data)
}

export async function testModelRoute(routeKey: string, prompt: string) {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/models/test', {
    route_key: routeKey,
    prompt,
  })
  return normalizeTestResult(response.data.data)
}
