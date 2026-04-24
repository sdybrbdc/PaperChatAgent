import type { AgentRunDTO, AgentRunNodeDTO, AgentWorkflowDTO, AgentWorkflowNodeDTO } from '../types/agents'
import { apiClient } from '../utils/http'

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
  request_id: string
}

function normalizeRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function normalizeNode(data: unknown): AgentWorkflowNodeDTO {
  const record = normalizeRecord(data)
  return {
    id: String(record.id ?? ''),
    parentNodeId: String(record.parent_node_id ?? ''),
    title: String(record.title ?? ''),
    type: String(record.type ?? 'workflow_node'),
    executorKey: String(record.executor_key ?? ''),
    fallbackExecutorKey: String(record.fallback_executor_key ?? ''),
    modelSlot: String(record.model_slot ?? 'conversation_model'),
    currentModelName: String(record.current_model_name ?? ''),
    inputSource: String(record.input_source ?? ''),
    outputTarget: String(record.output_target ?? ''),
    description: String(record.description ?? ''),
    handoffRule: String(record.handoff_rule ?? ''),
    config: normalizeRecord(record.config),
    subNodes: Array.isArray(record.sub_nodes) ? record.sub_nodes.map(normalizeNode) : [],
  }
}

function normalizeWorkflow(data: unknown): AgentWorkflowDTO {
  const record = normalizeRecord(data)
  return {
    id: String(record.id ?? ''),
    slug: String(record.slug ?? ''),
    name: String(record.name ?? ''),
    description: String(record.description ?? ''),
    sourceType: String(record.source_type ?? ''),
    status: String(record.status ?? ''),
    version: String(record.version ?? ''),
    nodeCount: Number(record.node_count ?? 0),
    updatedAt: (record.updated_at as string | null | undefined) ?? null,
    createdAt: (record.created_at as string | null | undefined) ?? null,
    definition: normalizeRecord(record.definition),
    nodes: Array.isArray(record.nodes) ? record.nodes.map(normalizeNode) : undefined,
  }
}

function normalizeRunNode(data: unknown): AgentRunNodeDTO {
  const record = normalizeRecord(data)
  return {
    id: String(record.id ?? ''),
    workflowRunId: String(record.workflow_run_id ?? ''),
    nodeId: String(record.node_id ?? ''),
    parentNodeId: String(record.parent_node_id ?? ''),
    title: String(record.title ?? ''),
    status: String(record.status ?? 'pending'),
    detail: String(record.detail ?? ''),
    progress: Number(record.progress ?? 0),
    input: normalizeRecord(record.input),
    output: normalizeRecord(record.output),
    metadata: normalizeRecord(record.metadata),
    errorText: String(record.error_text ?? ''),
    sortOrder: Number(record.sort_order ?? 0),
    startedAt: (record.started_at as string | null | undefined) ?? null,
    completedAt: (record.completed_at as string | null | undefined) ?? null,
  }
}

function normalizeRun(data: unknown): AgentRunDTO {
  const record = normalizeRecord(data)
  const report = normalizeRecord(record.report)
  return {
    id: String(record.id ?? ''),
    taskId: String(record.task_id ?? ''),
    workflowId: String(record.workflow_id ?? ''),
    workflowName: String(record.workflow_name ?? ''),
    conversationId: (record.conversation_id as string | null | undefined) ?? null,
    title: String(record.title ?? ''),
    status: String(record.status ?? 'pending'),
    currentNode: String(record.current_node ?? ''),
    progress: Number(record.progress ?? 0),
    summary: String(record.summary ?? ''),
    failedReason: String(record.failed_reason ?? ''),
    detailUrl: String(record.detail_url ?? ''),
    input: normalizeRecord(record.input),
    output: normalizeRecord(record.output),
    error: normalizeRecord(record.error),
    createdAt: (record.created_at as string | null | undefined) ?? null,
    updatedAt: (record.updated_at as string | null | undefined) ?? null,
    startedAt: (record.started_at as string | null | undefined) ?? null,
    completedAt: (record.completed_at as string | null | undefined) ?? null,
    report: record.report
      ? {
          id: String(report.id ?? ''),
          title: String(report.title ?? ''),
          content: String(report.content ?? ''),
          metadata: normalizeRecord(report.metadata),
          createdAt: (report.created_at as string | null | undefined) ?? null,
        }
      : null,
    nodes: Array.isArray(record.nodes) ? record.nodes.map(normalizeRunNode) : undefined,
  }
}

export async function getAgentWorkflows() {
  const response = await apiClient.get<ApiEnvelope<{ items: unknown[] }>>('/agents/workflows')
  return response.data.data.items.map(normalizeWorkflow)
}

export async function getAgentWorkflow(workflowId: string) {
  const response = await apiClient.get<ApiEnvelope<unknown>>(`/agents/workflows/${workflowId}`)
  return normalizeWorkflow(response.data.data)
}

export async function getAgentWorkflowNodes(workflowId: string) {
  const response = await apiClient.get<ApiEnvelope<{ items: unknown[] }>>(`/agents/workflows/${workflowId}/nodes`)
  return response.data.data.items.map(normalizeNode)
}

export async function saveAgentNodeConfig(
  workflowId: string,
  nodeId: string,
  payload: {
    executorKey: string
    fallbackExecutorKey: string
    modelSlot: string
    config: Record<string, unknown>
  },
) {
  const response = await apiClient.put<ApiEnvelope<unknown>>(`/agents/workflows/${workflowId}/nodes/${nodeId}/config`, {
    executor_key: payload.executorKey,
    fallback_executor_key: payload.fallbackExecutorKey,
    model_slot: payload.modelSlot,
    config: payload.config,
  })
  return normalizeNode(response.data.data)
}

export async function createAgentRun(workflowId: string, payload: { topic: string; maxPapers?: number }) {
  const response = await apiClient.post<ApiEnvelope<unknown>>(`/agents/workflows/${workflowId}/runs`, {
    topic: payload.topic,
    max_papers: payload.maxPapers ?? 6,
  })
  return normalizeRun(response.data.data)
}

export async function getAgentRun(runId: string) {
  const response = await apiClient.get<ApiEnvelope<unknown>>(`/agents/runs/${runId}`)
  return normalizeRun(response.data.data)
}

export async function getAgentRunNodes(runId: string) {
  const response = await apiClient.get<ApiEnvelope<{ items: unknown[] }>>(`/agents/runs/${runId}/nodes`)
  return response.data.data.items.map(normalizeRunNode)
}
