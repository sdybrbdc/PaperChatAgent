import type { TaskArtifactDTO, TaskCreatePayload, TaskDTO, TaskDetailDTO, TaskNodeRunDTO } from '../types/tasks'
import { apiClient } from '../utils/http'

interface ApiEnvelope<T> {
  data: T
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function list(value: unknown): unknown[] {
  if (Array.isArray(value)) return value
  const data = record(value)
  return Array.isArray(data.items) ? data.items : []
}

function normalizeTask(value: unknown): TaskDTO {
  const data = record(value)
  return {
    id: String(data.id ?? ''),
    title: String(data.title ?? ''),
    status: String(data.status ?? 'pending'),
    progress: Number(data.progress ?? 0),
    workflowId: String(data.workflow_id ?? data.workflowId ?? ''),
    workflowName: String(data.workflow_name ?? data.workflowName ?? ''),
    conversationId: (data.conversation_id as string | null | undefined) ?? (data.conversationId as string | null | undefined) ?? null,
    currentNode: String(data.current_node ?? data.currentNode ?? ''),
    summary: String(data.summary ?? ''),
    failedReason: String(data.failed_reason ?? data.failedReason ?? ''),
    payload: record(data.payload),
    createdAt: (data.created_at as string | null | undefined) ?? (data.createdAt as string | null | undefined) ?? null,
    updatedAt: (data.updated_at as string | null | undefined) ?? (data.updatedAt as string | null | undefined) ?? null,
    startedAt: (data.started_at as string | null | undefined) ?? (data.startedAt as string | null | undefined) ?? null,
    completedAt: (data.completed_at as string | null | undefined) ?? (data.completedAt as string | null | undefined) ?? null,
  }
}

function normalizeNode(value: unknown): TaskNodeRunDTO {
  const data = record(value)
  return {
    id: String(data.id ?? ''),
    nodeId: String(data.node_id ?? data.nodeId ?? ''),
    title: String(data.title ?? data.node_title ?? ''),
    status: String(data.status ?? 'pending'),
    progress: Number(data.progress ?? 0),
    detail: String(data.detail ?? ''),
    errorText: String(data.error_text ?? data.errorText ?? ''),
    startedAt: (data.started_at as string | null | undefined) ?? (data.startedAt as string | null | undefined) ?? null,
    completedAt: (data.completed_at as string | null | undefined) ?? (data.completedAt as string | null | undefined) ?? null,
  }
}

function normalizeArtifact(value: unknown): TaskArtifactDTO {
  const data = record(value)
  return {
    id: String(data.id ?? ''),
    taskId: String(data.task_id ?? data.taskId ?? ''),
    artifactType: String(data.artifact_type ?? data.artifactType ?? ''),
    title: String(data.title ?? ''),
    content: String(data.content ?? ''),
    uri: String(data.uri ?? ''),
    createdAt: (data.created_at as string | null | undefined) ?? (data.createdAt as string | null | undefined) ?? null,
  }
}

function normalizeDetail(value: unknown): TaskDetailDTO {
  const data = record(value)
  const task = normalizeTask(value)
  return {
    ...task,
    nodes: list(data.nodes ?? data.node_runs).map(normalizeNode),
    artifacts: list(data.artifacts).map(normalizeArtifact),
    workflowRun: data.workflow_run ? record(data.workflow_run) : data.workflowRun ? record(data.workflowRun) : null,
  }
}

export async function getTasks(params?: { status?: string; conversationId?: string; limit?: number }) {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/tasks', {
    params: {
      status: params?.status,
      conversation_id: params?.conversationId,
      limit: params?.limit ?? 50,
    },
  })
  return list(response.data.data).map(normalizeTask)
}

export async function createTask(payload: TaskCreatePayload) {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/tasks', {
    topic: payload.topic,
    workflow_id: payload.workflowId ?? 'smart_research_assistant',
    conversation_id: payload.conversationId || null,
    max_papers: payload.maxPapers ?? 6,
    start_background: payload.startBackground ?? true,
  })
  return normalizeDetail(response.data.data)
}

export async function getTaskDetail(taskId: string) {
  const response = await apiClient.get<ApiEnvelope<unknown>>(`/tasks/${taskId}`)
  return normalizeDetail(response.data.data)
}
