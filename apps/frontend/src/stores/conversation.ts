import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ChatSessionDTO, ChatStreamEventDTO, MessageDTO } from '../types/chat'
import { createConversation, getConversationMessages, getConversations, sendMessageStream } from '../apis/chat'

export const useConversationStore = defineStore('conversation', () => {
  const currentSession = ref<ChatSessionDTO | null>(null)
  const sessions = ref<ChatSessionDTO[]>([])
  const messages = ref<MessageDTO[]>([])
  const streamEvents = ref<string[]>([])
  const composerText = ref('')
  const isStreaming = ref(false)
  const errorMessage = ref('')

  async function load() {
    sessions.value = await getConversations()
    if (sessions.value.length === 0) {
      const created = await createConversation()
      sessions.value = [created]
    }

    const selectedSessionId = currentSession.value?.id ?? sessions.value[0]?.id
    if (selectedSessionId) {
      await selectConversation(selectedSessionId)
    }
  }

  function pushEvent(detail: string) {
    streamEvents.value = [detail, ...streamEvents.value].slice(0, 8)
  }

  function markActiveSession(sessionId: string) {
    sessions.value = sessions.value.map((session) => ({
      ...session,
      active: session.id === sessionId,
    }))
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

  function updateCurrentSessionPreview(message: MessageDTO) {
    if (!currentSession.value) return

    currentSession.value = {
      ...currentSession.value,
      title:
        currentSession.value.title === '新聊天'
          ? message.content.replace(/\s+/g, ' ').slice(0, 24) || '新聊天'
          : currentSession.value.title,
      lastMessagePreview: message.content.replace(/\s+/g, ' ').slice(0, 120),
      lastMessageAt: message.createdAt,
      updatedAt: message.createdAt,
      active: true,
    }

    sessions.value = sessions.value.map((session) =>
      session.id === currentSession.value?.id ? { ...currentSession.value! } : session,
    )
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
          updateCurrentSessionPreview(message)
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

  async function selectConversation(sessionId: string) {
    currentSession.value = sessions.value.find((session) => session.id === sessionId) ?? null
    markActiveSession(sessionId)
    messages.value = currentSession.value ? await getConversationMessages(currentSession.value.id) : []
    streamEvents.value = []
    errorMessage.value = ''
  }

  async function createNewConversation() {
    const created = await createConversation()
    sessions.value = [{ ...created, active: true }, ...sessions.value.map((session) => ({ ...session, active: false }))]
    await selectConversation(created.id)
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
    updateCurrentSessionPreview({
      id: `preview-${Date.now()}`,
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
    currentSession,
    sessions,
    messages,
    streamEvents,
    composerText,
    isStreaming,
    errorMessage,
    load,
    selectConversation,
    createNewConversation,
    sendCurrentMessage,
  }
})
