import type { SkillCreatePayload, SkillDTO, SkillImportPayload, SkillTestResultDTO } from '../types/skills'
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

function normalizeSkill(value: unknown): SkillDTO {
  const data = record(value)
  return {
    id: String(data.id ?? ''),
    name: String(data.name ?? ''),
    description: String(data.description ?? ''),
    sourceType: String(data.source_type ?? data.sourceType ?? ''),
    sourceUri: String(data.source_uri ?? data.sourceUri ?? ''),
    entrypoint: String(data.entrypoint ?? ''),
    status: String(data.status ?? 'enabled'),
    version: String(data.version ?? ''),
    inputSchema: record(data.input_schema ?? data.inputSchema),
    outputSchema: record(data.output_schema ?? data.outputSchema),
    createdAt: (data.created_at as string | null | undefined) ?? (data.createdAt as string | null | undefined) ?? null,
    updatedAt: (data.updated_at as string | null | undefined) ?? (data.updatedAt as string | null | undefined) ?? null,
  }
}

function normalizeTestResult(value: unknown): SkillTestResultDTO {
  const data = record(value)
  return {
    ok: Boolean(data.ok ?? data.success ?? false),
    message: String(data.message ?? ''),
    output: data.output ?? data.result ?? null,
    latencyMs: Number(data.latency_ms ?? data.latencyMs ?? 0),
    validation: record(data.validation),
  }
}

export async function getSkills() {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/skills')
  return list(response.data.data).map(normalizeSkill)
}

export async function createSkill(payload: SkillCreatePayload) {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/skills', {
    name: payload.name,
    description: payload.description ?? '',
    source_type: payload.sourceType ?? 'local',
    source_uri: payload.sourceUri ?? '',
    entrypoint: payload.entrypoint ?? '',
    status: payload.status ?? 'disabled',
    manifest: payload.manifest ?? {},
    input_schema: payload.inputSchema ?? {},
    output_schema: payload.outputSchema ?? {},
    metadata: payload.metadata ?? {},
  })
  return normalizeSkill(response.data.data)
}

export async function importLocalSkill(payload: SkillImportPayload) {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/skills/import-local', {
    source_uri: payload.sourceUri,
    status: payload.status ?? 'disabled',
  })
  return normalizeSkill(response.data.data)
}

export async function getCcSwitchSkills() {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/skills/sources/cc-switch')
  return {
    source: record(record(response.data.data).source),
    items: list(response.data.data).map(normalizeSkill),
  }
}

export async function syncCcSwitchSkills() {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/skills/sync/cc-switch')
  const data = record(response.data.data)
  return {
    source: record(data.source),
    created: Number(data.created ?? 0),
    updated: Number(data.updated ?? 0),
    total: Number(data.total ?? 0),
    items: list(data).map(normalizeSkill),
  }
}

export async function testSkill(skillId: string, input: Record<string, unknown>) {
  const response = await apiClient.post<ApiEnvelope<unknown>>(`/skills/${skillId}/test`, { input })
  return normalizeTestResult(response.data.data)
}
