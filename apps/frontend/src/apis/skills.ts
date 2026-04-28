import type {
  SkillCreatePayload,
  SkillDTO,
  SkillFileAddPayload,
  SkillFileDeletePayload,
  SkillFileUpdatePayload,
  SkillFolderNode,
  SkillImportPayload,
  SkillImportResultDTO,
  SkillTestResultDTO,
  SkillUpdatePayload,
} from '../types/skills'
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

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : []
}

function normalizeFolder(value: unknown): SkillFolderNode | null {
  const data = record(value)
  if (data.type !== 'folder') return null
  return {
    name: String(data.name ?? ''),
    path: String(data.path ?? ''),
    type: 'folder',
    folder: Array.isArray(data.folder)
      ? data.folder
          .map((item) => {
            const child = record(item)
            if (child.type === 'folder') return normalizeFolder(child)
            if (child.type === 'file') {
              return {
                name: String(child.name ?? ''),
                path: String(child.path ?? ''),
                type: 'file' as const,
                content: String(child.content ?? ''),
              }
            }
            return null
          })
          .filter((item): item is NonNullable<typeof item> => Boolean(item))
      : [],
  }
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
    manifest: record(data.manifest),
    inputSchema: record(data.input_schema ?? data.inputSchema),
    outputSchema: record(data.output_schema ?? data.outputSchema),
    metadata: record(data.metadata),
    folder: normalizeFolder(data.folder),
    content: String(data.content ?? ''),
    contentPreview: String(data.content_preview ?? data.contentPreview ?? ''),
    contentSource: String(data.content_source ?? data.contentSource ?? ''),
    fileCount: Number(data.file_count ?? data.fileCount ?? 0),
    asToolName: String(data.as_tool_name ?? data.asToolName ?? ''),
    triggerPhrases: stringList(data.trigger_phrases ?? data.triggerPhrases),
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

function createPayload(payload: SkillCreatePayload | SkillUpdatePayload) {
  return {
    name: payload.name,
    description: payload.description,
    source_type: payload.sourceType,
    source_uri: payload.sourceUri,
    entrypoint: payload.entrypoint,
    status: payload.status,
    content: payload.content,
    manifest: payload.manifest,
    input_schema: payload.inputSchema,
    output_schema: payload.outputSchema,
    metadata: payload.metadata,
  }
}

export async function getSkills() {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/skills')
  return list(response.data.data).map(normalizeSkill)
}

export async function getSkill(skillId: string) {
  const response = await apiClient.get<ApiEnvelope<unknown>>(`/skills/${skillId}`)
  return normalizeSkill(response.data.data)
}

export async function createSkill(payload: SkillCreatePayload) {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/skills', createPayload(payload))
  return normalizeSkill(response.data.data)
}

export async function updateSkill(skillId: string, payload: SkillUpdatePayload) {
  const response = await apiClient.patch<ApiEnvelope<unknown>>(`/skills/${skillId}`, createPayload(payload))
  return normalizeSkill(response.data.data)
}

export async function deleteSkill(skillId: string) {
  const response = await apiClient.delete<ApiEnvelope<unknown>>(`/skills/${skillId}`)
  return response.data.data
}

export async function importLocalSkill(payload: SkillImportPayload = {}) {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/skills/import-local', {
    source_uri: payload.sourceUri ?? '',
    status: payload.status ?? 'enabled',
  })
  const data = record(response.data.data)
  if (Array.isArray(data.items) || Array.isArray(data.created) || Array.isArray(data.skipped)) {
    return {
      created: stringList(data.created),
      skipped: stringList(data.skipped),
      failed: Array.isArray(data.failed)
        ? data.failed.map((item) => {
            const failed = record(item)
            return {
              name: String(failed.name ?? ''),
              path: String(failed.path ?? ''),
              error: String(failed.error ?? ''),
            }
          })
        : [],
      sourceCount: Number(data.source_count ?? data.sourceCount ?? 0),
      items: list(data).map(normalizeSkill),
    } satisfies SkillImportResultDTO
  }
  const skill = normalizeSkill(response.data.data)
  return {
    created: [skill.name],
    skipped: [],
    failed: [],
    sourceCount: 1,
    items: [skill],
  } satisfies SkillImportResultDTO
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

export async function updateSkillFile(skillId: string, payload: SkillFileUpdatePayload) {
  const response = await apiClient.patch<ApiEnvelope<unknown>>(`/skills/${skillId}/files`, payload)
  return normalizeSkill(response.data.data)
}

export async function addSkillFile(skillId: string, payload: SkillFileAddPayload) {
  const response = await apiClient.post<ApiEnvelope<unknown>>(`/skills/${skillId}/files`, payload)
  return normalizeSkill(response.data.data)
}

export async function deleteSkillFile(skillId: string, payload: SkillFileDeletePayload) {
  const response = await apiClient.delete<ApiEnvelope<unknown>>(`/skills/${skillId}/files`, { data: payload })
  return normalizeSkill(response.data.data)
}

export async function testSkill(skillId: string, input: Record<string, unknown>) {
  const response = await apiClient.post<ApiEnvelope<unknown>>(`/skills/${skillId}/test`, { input })
  return normalizeTestResult(response.data.data)
}
