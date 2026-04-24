import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ChatSessionDTO, ChatStreamEventDTO, ConversationGuidanceDTO, MessageDTO } from '../types/chat'
import {
  createConversation,
  generateConversationDraft,
  getConversationGuidance,
  getConversationMessages,
  getConversations,
  sendMessageStream,
} from '../apis/chat'


function buildDefaultGuidance(): ConversationGuidanceDTO {
  return {
    status: 'casual_chat',
    headline: '你可以先像普通聊天一样交流问题，系统会在对话逐渐收敛后给出更专业的研究提示。',
    sections: [
      {
        key: 'casual_hint',
        title: '当前判断',
        style: 'compact',
        text: '普通交流中，先把问题说清楚即可。',
        items: [],
      },
    ],
    draft: null,
    updatedAt: null,
  }
}


export const useConversationStore = defineStore('conversation', () => {
  const isLoading = ref(false)
  const currentConversation = ref<ChatSessionDTO | null>(null)
  const conversations = ref<ChatSessionDTO[]>([])
  const messages = ref<MessageDTO[]>([])
  const guidance = ref<ConversationGuidanceDTO>(buildDefaultGuidance())
  const composerText = ref('')
  const isStreaming = ref(false)
  const isGeneratingDraft = ref(false)
  const errorMessage = ref('')
  const guidanceError = ref('')

  function markActiveConversation(conversationId: string) {
    conversations.value = conversations.value.map((conversation) => ({
      ...conversation,
      active: conversation.id === conversationId,
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

  function syncConversation(updated: ChatSessionDTO) {
    currentConversation.value = { ...updated, active: true }
    conversations.value = conversations.value.map((conversation) =>
      conversation.id === updated.id ? { ...updated, active: true } : { ...conversation, active: false },
    )
  }

  function handleStreamEvent(event: ChatStreamEventDTO) {
    switch (event.event) {
      case 'message.delta': {
        const draft = messages.value.find((message) => message.isDraft)
        const delta = String(event.data.delta ?? '')
        const accumulated = String(event.data.accumulated ?? '')
        if (draft) {
          draft.content = accumulated || `${draft.content}${delta}`
        }
        break
      }
      case 'message.completed': {
        const message = event.data.message as MessageDTO | undefined
        const conversation = event.data.conversation as ChatSessionDTO | undefined
        if (message) {
          replaceDraftWith(message)
        }
        if (conversation) {
          syncConversation(conversation)
        }
        break
      }
      case 'guidance.updated': {
        const updatedGuidance = event.data.guidance as ConversationGuidanceDTO | undefined
        const conversation = event.data.conversation as ChatSessionDTO | undefined
        if (updatedGuidance) {
          guidance.value = updatedGuidance
          guidanceError.value = ''
        }
        if (conversation) {
          syncConversation(conversation)
        }
        break
      }
      case 'message.failed':
        removeDraft()
        errorMessage.value = String(event.data.message ?? '流式消息生成失败')
        break
      default:
        break
    }
  }

  async function selectConversation(conversationId: string) {
    currentConversation.value = conversations.value.find((conversation) => conversation.id === conversationId) ?? null
    markActiveConversation(conversationId)
    if (!currentConversation.value) {
      messages.value = []
      guidance.value = buildDefaultGuidance()
      return
    }

    const [loadedMessages, loadedGuidance] = await Promise.all([
      getConversationMessages(conversationId),
      getConversationGuidance(conversationId).catch(() => buildDefaultGuidance()),
    ])
    messages.value = loadedMessages
    guidance.value = loadedGuidance
    errorMessage.value = ''
    guidanceError.value = ''
  }

  async function createNewConversation() {
    const created = await createConversation()
    conversations.value = [
      { ...created, active: true },
      ...conversations.value.map((conversation) => ({ ...conversation, active: false })),
    ]
    await selectConversation(created.id)
  }

  async function load() {
    if (isLoading.value) return
    isLoading.value = true
    try {
      conversations.value = await getConversations()
      if (conversations.value.length === 0) {
        await createNewConversation()
        return
      }
      const selectedConversationId = currentConversation.value?.id ?? conversations.value[0]?.id
      if (selectedConversationId) {
        await selectConversation(selectedConversationId)
      }
    } finally {
      isLoading.value = false
    }
  }

  async function sendCurrentMessage() {
    const content = composerText.value.trim()
    if (!content || !currentConversation.value || isStreaming.value) return

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
          conversationId: currentConversation.value.id,
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

  async function generateDraft() {
    if (!currentConversation.value || isGeneratingDraft.value) return
    isGeneratingDraft.value = true
    guidanceError.value = ''
    try {
      guidance.value = await generateConversationDraft(currentConversation.value.id)
    } catch (error) {
      guidanceError.value = error instanceof Error ? error.message : '研究方案生成失败'
    } finally {
      isGeneratingDraft.value = false
    }
  }

  return {
    currentConversation,
    conversations,
    messages,
    guidance,
    composerText,
    isStreaming,
    isGeneratingDraft,
    errorMessage,
    guidanceError,
    isLoading,
    load,
    selectConversation,
    createNewConversation,
    sendCurrentMessage,
    generateDraft,
  }
})
