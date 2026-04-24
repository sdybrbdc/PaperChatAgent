export interface AgentWorkflowDTO {
  id: string
  slug: string
  name: string
  description: string
  sourceType: string
  status: string
  version: string
  nodeCount: number
  updatedAt: string | null
  createdAt: string | null
  definition?: Record<string, unknown>
  nodes?: AgentWorkflowNodeDTO[]
}

export interface AgentWorkflowNodeDTO {
  id: string
  parentNodeId: string
  title: string
  type: string
  executorKey: string
  fallbackExecutorKey: string
  modelSlot: string
  currentModelName: string
  inputSource: string
  outputTarget: string
  description: string
  handoffRule: string
  config: Record<string, unknown>
  subNodes: AgentWorkflowNodeDTO[]
}

export interface AgentRunDTO {
  id: string
  taskId: string
  workflowId: string
  workflowName: string
  conversationId: string | null
  title: string
  status: string
  currentNode: string
  progress: number
  summary: string
  failedReason: string
  detailUrl: string
  input: Record<string, unknown>
  output: Record<string, unknown>
  error: Record<string, unknown>
  createdAt: string | null
  updatedAt: string | null
  startedAt: string | null
  completedAt: string | null
  report: AgentRunReportDTO | null
  nodes?: AgentRunNodeDTO[]
}

export interface AgentRunReportDTO {
  id: string
  title: string
  content: string
  metadata: Record<string, unknown>
  createdAt: string | null
}

export interface AgentRunNodeDTO {
  id: string
  workflowRunId: string
  nodeId: string
  parentNodeId: string
  title: string
  status: string
  detail: string
  progress: number
  input: Record<string, unknown>
  output: Record<string, unknown>
  metadata: Record<string, unknown>
  errorText: string
  sortOrder: number
  startedAt: string | null
  completedAt: string | null
}
