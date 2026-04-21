import { MOCK_GLOBAL_KB, MOCK_KNOWLEDGE_RAIL, MOCK_PRIVATE_KB } from '../mocks/knowledge'

export async function getKnowledgeOverviewMock() {
  return {
    global: MOCK_GLOBAL_KB,
    private: MOCK_PRIVATE_KB,
    rail: MOCK_KNOWLEDGE_RAIL,
  }
}
