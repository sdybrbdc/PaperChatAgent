import type {
  ChatSessionDTO,
  ChatStreamEventDTO,
  ConversationHistoryGroup,
  InboxConversationDTO,
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

function normalizeInbox(data: Record<string, unknown>): InboxConversationDTO {
  return {
    id: String(data.id ?? ''),
    title: String(data.title ?? ''),
    status: (data.status as 'active' | 'archived') ?? 'active',
    summary: String(data.summary ?? ''),
    lastMessageAt: (data.last_message_at as string | null | undefined) ?? null,
  }
}

function normalizeSession(data: Record<string, unknown>): ChatSessionDTO {
  return {
    id: String(data.id ?? ''),
    title: String(data.title ?? ''),
    scope: (data.scope as 'inbox' | 'workspace') ?? 'inbox',
    status: (data.status as 'active' | 'archived' | undefined) ?? 'active',
    lastMessageAt: (data.last_message_at as string | null | undefined) ?? null,
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

export async function getInboxConversation() {
  const response = await apiClient.get<
    ApiEnvelope<{
      conversation: Record<string, unknown>
      current_session: Record<string, unknown>
    }>
  >('/conversations/inbox')

  return {
    conversation: normalizeInbox(response.data.data.conversation),
    currentSession: normalizeSession(response.data.data.current_session),
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

export async function getConversationHistoryGroups(): Promise<ConversationHistoryGroup[]> {
  const [inboxResponse, workspacesResponse] = await Promise.all([
    getInboxConversation(),
    apiClient.get<
      ApiEnvelope<{
        items: Array<Record<string, unknown>>
      }>
    >('/workspaces'),
  ])

  const historyGroups: ConversationHistoryGroup[] = [
    {
      id: inboxResponse.conversation.id,
      title: inboxResponse.conversation.title,
      subtitle: inboxResponse.conversation.summary,
      type: 'inbox',
    },
  ]

  for (const item of workspacesResponse.data.data.items) {
    historyGroups.push({
      id: String(item.id ?? ''),
      title: `工作区：${String(item.name ?? '')}`,
      subtitle: String(item.description ?? ''),
      items: [],
      type: 'workspace',
    })
  }

  return historyGroups
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
