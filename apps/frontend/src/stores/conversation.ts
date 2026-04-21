import { ref } from 'vue'
import { defineStore } from 'pinia'
import type {
  ChatSessionDTO,
  ConversationHistoryGroup,
  InboxConversationDTO,
  MessageDTO,
  TaskSuggestionDTO,
} from '../types/chat'
import {
  getChatRailMock,
  getChatSessionMock,
  getHistoryGroupsMock,
  getInboxConversationMock,
  getMessagesMock,
  getTaskSuggestionMock,
} from '../apis/chat'

export const useConversationStore = defineStore('conversation', () => {
  const inboxConversation = ref<InboxConversationDTO | null>(null)
  const currentSession = ref<ChatSessionDTO | null>(null)
  const messages = ref<MessageDTO[]>([])
  const historyGroups = ref<ConversationHistoryGroup[]>([])
  const taskSuggestion = ref<TaskSuggestionDTO | null>(null)
  const railCards = ref<{ title: string; lines: string[] }[]>([])

  async function load() {
    inboxConversation.value = await getInboxConversationMock()
    currentSession.value = await getChatSessionMock()
    messages.value = await getMessagesMock()
    historyGroups.value = await getHistoryGroupsMock()
    taskSuggestion.value = await getTaskSuggestionMock()
    railCards.value = await getChatRailMock()
  }

  return {
    inboxConversation,
    currentSession,
    messages,
    historyGroups,
    taskSuggestion,
    railCards,
    load,
  }
})
