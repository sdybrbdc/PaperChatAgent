import type {
  ChatSessionDTO,
  ChatStreamEventDTO,
  MessageDTO,
} from '../types/chat'
import { apiClient } from '../utils/http'
import { openJsonEventStream } from '../utils/stream'

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
  request_id: string
}

function normalizeSession(data: Record<string, unknown>): ChatSessionDTO {
  return {
    id: String(data.id ?? ''),
    title: String(data.title ?? ''),
    scope: (data.scope as 'inbox' | 'workspace') ?? 'inbox',
    status: (data.status as 'active' | 'archived' | undefined) ?? 'active',
    lastMessageAt: (data.last_message_at as string | null | undefined) ?? null,
    updatedAt: (data.updated_at as string | null | undefined) ?? null,
    lastMessagePreview: String(data.last_message_preview ?? ''),
  }
}

function normalizeMessage(data: Record<string, unknown>): MessageDTO {
  return {
    id: String(data.id ?? ''),
    role: (data.role as 'user' | 'assistant' | 'system') ?? 'assistant',
    messageType: (data.message_type as 'chat' | 'task_suggestion' | 'system_notice') ?? 'chat',
    content: String(data.content ?? ''),
    metadata: (data.metadata as Record<string, unknown> | undefined) ?? {},
    citations: (data.citations as Array<Record<string, unknown>> | undefined) ?? [],
    createdAt: String(data.created_at ?? new Date().toISOString()),
  }
}

export async function getConversationMessages(sessionId: string) {
  const response = await apiClient.get<
    ApiEnvelope<{
      items: Array<Record<string, unknown>>
    }>
  >(`/conversations/${sessionId}/messages`)

  return response.data.data.items.map(normalizeMessage)
}

export async function getConversations() {
  const response = await apiClient.get<
    ApiEnvelope<{
      items: Array<Record<string, unknown>>
    }>
  >('/conversations')

  return response.data.data.items.map(normalizeSession)
}

export async function createConversation() {
  const response = await apiClient.post<ApiEnvelope<Record<string, unknown>>>('/conversations', {})
  return normalizeSession(response.data.data)
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
        onEvent({
          event: event.event as ChatStreamEventDTO['event'],
          data: {
            message: rawMessage ? normalizeMessage(rawMessage) : undefined,
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
