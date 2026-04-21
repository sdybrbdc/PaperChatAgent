export interface InboxConversationDTO {
  id: string
  title: string
  status: 'active' | 'archived'
  summary: string
}

export interface ChatSessionDTO {
  id: string
  title: string
  scope: 'inbox' | 'workspace'
}

export interface MessageDTO {
  id: string
  role: 'user' | 'assistant' | 'system'
  messageType: 'chat' | 'task_suggestion' | 'system_notice'
  content: string
  createdAt: string
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
