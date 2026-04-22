import type { WorkflowNodeDTO, WorkflowSideCardDTO } from '../types/agents'
import { apiClient } from '../utils/http'

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
  request_id: string
}

export async function getWorkflowDefinition() {
  const workflowId = 'paperchat-default-workflow'
  const response = await apiClient.get<
    ApiEnvelope<{
      items: Array<Record<string, unknown>>
    }>
  >(`/agents/workflows/${workflowId}/nodes`)

  const nodes: WorkflowNodeDTO[] = response.data.data.items.map((item) => ({
    id: String(item.id ?? ''),
    title: String(item.title ?? ''),
    description: String(item.description ?? ''),
    tone: 'default',
  }))

  const rail: WorkflowSideCardDTO[] = [
    {
      title: '工作流来源',
      lines: ['当前节点定义来自真实 backend 接口', '状态仍为第一阶段占位值', '后续会接 workflow run 真实状态'],
    },
  ]

  return { nodes, rail }
}
