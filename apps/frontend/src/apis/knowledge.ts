import type { KnowledgeBaseDTO, KnowledgeSideCardDTO } from '../types/knowledge'
import { apiClient } from '../utils/http'

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
  request_id: string
}

function normalizeKnowledgeBase(base: Record<string, unknown> | undefined): KnowledgeBaseDTO {
  const files = (base?.files as Array<Record<string, unknown>> | undefined) ?? []
  return {
    id: String(base?.id ?? ''),
    title: String(base?.title ?? ''),
    description: String(base?.description ?? ''),
    files: files.map((file) => ({
      id: String(file.id ?? ''),
      title: String(file.title ?? ''),
      subtitle: `${String(file.source_type ?? '')} / ${String(file.index_status ?? '')}`,
    })),
  }
}

export async function getKnowledgeOverview() {
  const response = await apiClient.get<
    ApiEnvelope<{
      global: Record<string, unknown>
      private: Record<string, unknown>
      rail: KnowledgeSideCardDTO[]
    }>
  >('/knowledge')

  return {
    global: normalizeKnowledgeBase(response.data.data.global),
    private: normalizeKnowledgeBase(response.data.data.private),
    rail: response.data.data.rail,
  }
}
