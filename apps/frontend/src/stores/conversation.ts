import { ref } from 'vue'
import { defineStore } from 'pinia'
import type {
  ChatSessionDTO,
  ChatStreamEventDTO,
  ConversationHistoryGroup,
  InboxConversationDTO,
  MessageDTO,
  TaskSuggestionDTO,
} from '../types/chat'
import {
  getConversationMessages,
  getConversationHistoryGroups,
  getInboxConversation,
  sendMessageStream,
} from '../apis/chat'

export const useConversationStore = defineStore('conversation', () => {
  const inboxConversation = ref<InboxConversationDTO | null>(null)
  const currentSession = ref<ChatSessionDTO | null>(null)
  const messages = ref<MessageDTO[]>([])
  const historyGroups = ref<ConversationHistoryGroup[]>([])
  const taskSuggestion = ref<TaskSuggestionDTO | null>(null)
  const railCards = ref<{ title: string; lines: string[] }[]>([])
  const streamEvents = ref<string[]>([])
  const composerText = ref('')
  const isStreaming = ref(false)
  const errorMessage = ref('')

  async function load() {
    const inboxData = await getInboxConversation()
    inboxConversation.value = inboxData.conversation
    currentSession.value = inboxData.currentSession
    messages.value = currentSession.value ? await getConversationMessages(currentSession.value.id) : []
    historyGroups.value = await getConversationHistoryGroups()
    railCards.value = []
    syncTaskSuggestion()
  }

  function syncTaskSuggestion() {
    const suggestionMessage = [...messages.value]
      .reverse()
      .find((message) => message.messageType === 'task_suggestion')
    const metadataSuggestion = suggestionMessage?.metadata?.taskSuggestion
    taskSuggestion.value = (metadataSuggestion as TaskSuggestionDTO | undefined) ?? null
  }

  function pushEvent(detail: string) {
    streamEvents.value = [detail, ...streamEvents.value].slice(0, 8)
  }

  function replaceDraftWith(message: MessageDTO) {
    const draftIndex = messages.value.findIndex((item) => item.isDraft)
    if (draftIndex >= 0) {
      messages.value.splice(draftIndex, 1, message)
      return
    }
    messages.value.push(message)
  }

  function removeDraft() {
    messages.value = messages.value.filter((message) => !message.isDraft)
  }

  function handleStreamEvent(event: ChatStreamEventDTO) {
    switch (event.event) {
      case 'message.started':
        pushEvent('开始生成回复')
        break
      case 'message.delta': {
        const draft = messages.value.find((message) => message.isDraft)
        const delta = String(event.data.delta ?? '')
        const accumulated = String(event.data.accumulated ?? '')
        if (draft) {
          draft.content = accumulated || `${draft.content}${delta}`
        }
        break
      }
      case 'message.progress':
      case 'message.info':
      case 'message.tool':
        pushEvent(String(event.data.detail ?? event.event))
        break
      case 'message.completed': {
        const message = event.data.message as MessageDTO | undefined
        if (message) {
          replaceDraftWith(message)
          syncTaskSuggestion()
        }
        break
      }
      case 'message.failed':
        removeDraft()
        errorMessage.value = String(event.data.message ?? '流式消息生成失败')
        pushEvent(errorMessage.value)
        break
      case 'ping':
        break
    }
  }

  async function sendCurrentMessage() {
    const content = composerText.value.trim()
    if (!content || !currentSession.value || isStreaming.value) return

    errorMessage.value = ''
    const now = new Date().toISOString()
    messages.value.push({
      id: `local-user-${Date.now()}`,
      role: 'user',
      messageType: 'chat',
      content,
      createdAt: now,
    })
    messages.value.push({
      id: `draft-${Date.now()}`,
      role: 'assistant',
      messageType: 'chat',
      content: '',
      createdAt: now,
      isDraft: true,
    })
    composerText.value = ''
    isStreaming.value = true

    const controller = new AbortController()
    try {
      await sendMessageStream(
        {
          conversationId: currentSession.value.id,
          content,
          clientMessageId: `client-${Date.now()}`,
        },
        handleStreamEvent,
        controller.signal,
      )
    } catch (error) {
      removeDraft()
      errorMessage.value = error instanceof Error ? error.message : '流式消息生成失败'
    } finally {
      isStreaming.value = false
      controller.abort()
    }
  }

  return {
    inboxConversation,
    currentSession,
    messages,
    historyGroups,
    taskSuggestion,
    railCards,
    streamEvents,
    composerText,
    isStreaming,
    errorMessage,
    load,
    sendCurrentMessage,
  }
})
