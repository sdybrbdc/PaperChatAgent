export interface TaskDTO {
  id: string
  runId: string | null
  title: string
  status: string
  progress: number
  workflowId: string
  workflowName: string
  conversationId: string | null
  currentNode: string
  summary: string
  failedReason: string
  detailUrl: string
  agentDetailUrl: string
  payload: Record<string, unknown>
  input: Record<string, unknown>
  output: Record<string, unknown>
  error: Record<string, unknown>
  createdAt: string | null
  updatedAt: string | null
  startedAt: string | null
  completedAt: string | null
}

export interface TaskNodeRunDTO {
  id: string
  nodeId: string
  parentNodeId: string
  title: string
  status: string
  progress: number
  detail: string
  errorText: string
  sortOrder: number
  startedAt: string | null
  completedAt: string | null
}

export interface TaskArtifactDTO {
  id: string
  taskId: string
  artifactType: string
  title: string
  content: string
  uri: string
  metadata: Record<string, unknown>
  createdAt: string | null
}

export interface TaskDetailDTO extends TaskDTO {
  nodes: TaskNodeRunDTO[]
  artifacts: TaskArtifactDTO[]
  workflowRun: Record<string, unknown> | null
}

export interface TaskCreatePayload {
  topic: string
  workflowId?: string
  conversationId?: string
  maxPapers?: number
  startBackground?: boolean
}
