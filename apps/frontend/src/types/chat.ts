export type GuidanceStatus =
  | 'casual_chat'
  | 'topic_exploration'
  | 'needs_more_info'
  | 'ready_for_draft'
  | 'draft_ready'

export type GuidanceSectionStyle = 'info' | 'compact' | 'list' | 'warning' | 'draft_entry'

export interface ChatSessionDTO {
  id: string
  title: string
  status: 'active' | 'archived'
  active?: boolean
}

export interface MessageDTO {
  id: string
  role: 'user' | 'assistant' | 'system'
  messageType: 'chat' | 'task_event' | 'tool_result' | 'system_notice'
  content: string
  metadata?: Record<string, unknown> & {
    tool_calls?: MessageToolCallDTO[]
  }
  citations?: Array<Record<string, unknown>>
  createdAt: string
  isDraft?: boolean
}

export interface MessageToolCallDTO {
  capability_key: string
  kind: string
  name: string
  reason?: string
  status: 'running' | 'succeeded' | 'failed'
  summary?: string
}

export interface ResearchDraftDTO {
  title: string
  topic: string
  objective: string
  scope: string
  suggestedMaterials: string[]
  suggestedAgents: string[]
  nextActions: string[]
}

export interface ConversationGuidanceSectionDTO {
  key: string
  title: string
  style: GuidanceSectionStyle
  text?: string
  items?: string[]
}

export interface ConversationGuidanceDTO {
  status: GuidanceStatus
  headline: string
  sections: ConversationGuidanceSectionDTO[]
  draft: ResearchDraftDTO | null
  updatedAt?: string | null
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
    | 'guidance.updated'
    | 'ping'
  data: Record<string, unknown>
}
