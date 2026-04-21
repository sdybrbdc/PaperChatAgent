import {
  MOCK_CHAT_RAIL,
  MOCK_CHAT_SESSION,
  MOCK_HISTORY_GROUPS,
  MOCK_INBOX_CONVERSATION,
  MOCK_MESSAGES,
  MOCK_TASK_SUGGESTION,
} from '../mocks/chat'

export async function getInboxConversationMock() {
  return MOCK_INBOX_CONVERSATION
}

export async function getChatSessionMock() {
  return MOCK_CHAT_SESSION
}

export async function getHistoryGroupsMock() {
  return MOCK_HISTORY_GROUPS
}

export async function getMessagesMock() {
  return MOCK_MESSAGES
}

export async function getTaskSuggestionMock() {
  return MOCK_TASK_SUGGESTION
}

export async function getChatRailMock() {
  return MOCK_CHAT_RAIL
}
