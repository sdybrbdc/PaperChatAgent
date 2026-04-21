import { MOCK_WORKFLOW_NODES, MOCK_WORKFLOW_RAIL } from '../mocks/agents'

export async function getWorkflowDefinitionMock() {
  return {
    nodes: MOCK_WORKFLOW_NODES,
    rail: MOCK_WORKFLOW_RAIL,
  }
}
