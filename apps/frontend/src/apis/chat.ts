import type {
  ChatSessionDTO,
  ChatStreamEventDTO,
  ConversationGuidanceDTO,
  ConversationGuidanceSectionDTO,
  MessageDTO,
  ResearchDraftDTO,
} from '../types/chat'
import { apiClient } from '../utils/http'
import { openJsonEventStream } from '../utils/stream'

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
  request_id: string
}

function normalizeConversation(data: Record<string, unknown>): ChatSessionDTO {
  return {
    id: String(data.id ?? ''),
    title: String(data.title ?? ''),
    status: (data.status as 'active' | 'archived' | undefined) ?? 'active',
  }
}

function normalizeMessage(data: Record<string, unknown>): MessageDTO {
  return {
    id: String(data.id ?? ''),
    role: (data.role as 'user' | 'assistant' | 'system') ?? 'assistant',
    messageType: String(data.message_type ?? 'chat') as MessageDTO['messageType'],
    content: String(data.content ?? ''),
    metadata: (data.metadata as Record<string, unknown> | undefined) ?? {},
    citations: (data.citations as Array<Record<string, unknown>> | undefined) ?? [],
    createdAt: String(data.created_at ?? new Date().toISOString()),
  }
}

function normalizeStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : []
}

function normalizeDraft(data: unknown): ResearchDraftDTO | null {
  if (!data || typeof data !== 'object') return null
  const record = data as Record<string, unknown>
  return {
    title: String(record.title ?? ''),
    topic: String(record.topic ?? ''),
    objective: String(record.objective ?? ''),
    scope: String(record.scope ?? ''),
    suggestedMaterials: normalizeStringList(record.suggested_materials),
    suggestedAgents: normalizeStringList(record.suggested_agents),
    nextActions: normalizeStringList(record.next_actions),
  }
}

function normalizeSection(data: unknown): ConversationGuidanceSectionDTO | null {
  if (!data || typeof data !== 'object') return null
  const record = data as Record<string, unknown>
  return {
    key: String(record.key ?? ''),
    title: String(record.title ?? ''),
    style:
      (record.style as ConversationGuidanceSectionDTO['style']) ??
      'compact',
    text: record.text ? String(record.text) : '',
    items: normalizeStringList(record.items),
  }
}

function normalizeGuidance(data: Record<string, unknown>): ConversationGuidanceDTO {
  return {
    status:
      (data.status as ConversationGuidanceDTO['status']) ??
      'casual_chat',
    headline: String(data.headline ?? ''),
    sections: Array.isArray(data.sections)
      ? data.sections.map(normalizeSection).filter((item): item is ConversationGuidanceSectionDTO => Boolean(item))
      : [],
    draft: normalizeDraft(data.draft),
    updatedAt: (data.updated_at as string | null | undefined) ?? null,
  }
}

export async function getConversations() {
  const response = await apiClient.get<ApiEnvelope<{ items: Array<Record<string, unknown>> }>>('/conversations')
  return response.data.data.items.map(normalizeConversation)
}

export async function createConversation() {
  const response = await apiClient.post<ApiEnvelope<Record<string, unknown>>>('/conversations', {})
  return normalizeConversation(response.data.data)
}

export async function getConversationMessages(conversationId: string) {
  const response = await apiClient.get<ApiEnvelope<{ items: Array<Record<string, unknown>> }>>(
    `/conversations/${conversationId}/messages`,
  )
  return response.data.data.items.map(normalizeMessage)
}

export async function getConversationGuidance(conversationId: string) {
  const response = await apiClient.get<ApiEnvelope<Record<string, unknown>>>(`/conversations/${conversationId}/guidance`)
  return normalizeGuidance(response.data.data)
}

export async function generateConversationDraft(conversationId: string) {
  const response = await apiClient.post<ApiEnvelope<Record<string, unknown>>>(
    `/conversations/${conversationId}/guidance/draft`,
    {},
  )
  return normalizeGuidance(response.data.data)
}

export interface SendMessageStreamPayload {
  conversationId: string
  content: string
  clientMessageId?: string
}

export async function sendMessageStream(
  payload: SendMessageStreamPayload,
  onEvent: (event: ChatStreamEventDTO) => void,
  signal?: AbortSignal,
) {
  await openJsonEventStream({
    path: `/conversations/${payload.conversationId}/messages/stream`,
    method: 'POST',
    body: {
      content: payload.content,
      client_message_id: payload.clientMessageId,
      attachment_ids: [],
      metadata: {},
    },
    signal,
    onEvent: (event) => {
      if (event.event === 'message.completed') {
        const rawMessage = event.data.message as Record<string, unknown> | undefined
        const rawConversation = event.data.conversation as Record<string, unknown> | undefined
        onEvent({
          event: 'message.completed',
          data: {
            message: rawMessage ? normalizeMessage(rawMessage) : undefined,
            conversation: rawConversation ? normalizeConversation(rawConversation) : undefined,
          },
        })
        return
      }

      if (event.event === 'guidance.updated') {
        const rawGuidance = event.data.guidance as Record<string, unknown> | undefined
        const rawConversation = event.data.conversation as Record<string, unknown> | undefined
        onEvent({
          event: 'guidance.updated',
          data: {
            guidance: rawGuidance ? normalizeGuidance(rawGuidance) : undefined,
            conversation: rawConversation ? normalizeConversation(rawConversation) : undefined,
          },
        })
        return
      }

      onEvent({
        event: event.event as ChatStreamEventDTO['event'],
        data: event.data,
      })
    },
  })
}
