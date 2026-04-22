export interface InboxConversationDTO {
  id: string
  title: string
  status: 'active' | 'archived'
  summary: string
  lastMessageAt?: string | null
}

export interface ChatSessionDTO {
  id: string
  title: string
  scope: 'inbox' | 'workspace'
  status?: 'active' | 'archived'
  lastMessageAt?: string | null
}

export interface MessageDTO {
  id: string
  role: 'user' | 'assistant' | 'system'
  messageType: 'chat' | 'task_suggestion' | 'system_notice'
  content: string
  metadata?: Record<string, unknown>
  citations?: Array<Record<string, unknown>>
  createdAt: string
  isDraft?: boolean
}

export interface TaskSuggestionDTO {
  title: string
  topic: string
  sources: string
  outputs: string
  nextStep: string
  statusLabel: string
}

export interface ConversationHistoryGroup {
  id: string
  title: string
  subtitle?: string
  items?: string[]
  type?: 'inbox' | 'workspace'
}

export interface ChatStreamEventDTO {
  event:
    | 'message.started'
    | 'message.delta'
    | 'message.progress'
    | 'message.tool'
    | 'message.info'
    | 'message.completed'
    | 'message.failed'
    | 'ping'
  data: Record<string, unknown>
}
