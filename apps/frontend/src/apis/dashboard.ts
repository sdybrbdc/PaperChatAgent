import type {
  DashboardActivityDTO,
  DashboardEventDTO,
  DashboardInsightDTO,
  DashboardMetricPointDTO,
  DashboardOverviewDTO,
  DashboardSnapshotDTO,
  ModelUsageDTO,
  TaskUsageDTO,
  ToolUsageDTO,
} from '../types/dashboard'
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

function point(label: string, value: unknown): DashboardMetricPointDTO {
  return { label, value: Number(value ?? 0) }
}

function normalizeOverview(value: unknown): DashboardOverviewDTO {
  const data = record(value)
  const distribution = data.task_status_distribution ?? data.taskStatusDistribution
  const taskStatusDistribution = Array.isArray(distribution)
    ? distribution.map((item) => {
        const row = record(item)
        return point(String(row.label ?? row.status ?? ''), row.value ?? row.count)
      })
    : Object.entries(record(distribution)).map(([label, value]) => point(label, value))

  return {
    modelCallCount: Number(data.model_call_count ?? data.modelCallCount ?? 0),
    inputTokenCount: Number(data.input_token_count ?? data.inputTokenCount ?? 0),
    outputTokenCount: Number(data.output_token_count ?? data.outputTokenCount ?? 0),
    tokenCount: Number(data.token_count ?? data.tokenCount ?? 0),
    recentTaskCount: Number(data.recent_task_count ?? data.recentTaskCount ?? 0),
    activeTaskCount: Number(data.active_task_count ?? data.activeTaskCount ?? 0),
    failedTaskCount: Number(data.failed_task_count ?? data.failedTaskCount ?? 0),
    toolCallCount: Number(data.tool_call_count ?? data.toolCallCount ?? 0),
    taskStatusDistribution,
    averageLatencyMs: Number(record(data.usage).avg_latency_ms ?? record(data.health).avg_latency_ms ?? data.averageLatencyMs ?? 0),
    taskCompletionRate: Number(record(data.tasks).completion_rate ?? record(data.health).task_completion_rate ?? data.taskCompletionRate ?? 0),
    taskFailureRate: Number(record(data.health).task_failure_rate ?? data.taskFailureRate ?? 0),
  }
}

function normalizeModelUsage(value: unknown): ModelUsageDTO {
  const data = record(value)
  return {
    providerName: String(data.provider_name ?? data.providerName ?? ''),
    modelName: String(data.model_name ?? data.modelName ?? ''),
    callCount: Number(data.call_count ?? data.callCount ?? 0),
    inputTokens: Number(data.input_tokens ?? data.inputTokens ?? 0),
    outputTokens: Number(data.output_tokens ?? data.outputTokens ?? 0),
    totalTokens: Number(data.total_tokens ?? data.totalTokens ?? 0),
    successCount: Number(data.success_count ?? data.successCount ?? 0),
    errorCount: Number(data.error_count ?? data.errorCount ?? 0),
    successRate: Number(data.success_rate ?? data.successRate ?? 0),
    latencyMs: Number(data.latency_ms ?? data.latencyMs ?? 0),
    routeKey: String(data.route_key ?? data.routeKey ?? ''),
  }
}

function normalizeTaskUsage(value: unknown): TaskUsageDTO {
  const data = record(value)
  return {
    status: String(data.status ?? ''),
    currentNode: String(data.current_node ?? data.currentNode ?? ''),
    count: Number(data.count ?? 0),
    averageProgress: Number(data.average_progress ?? data.averageProgress ?? 0),
  }
}

function normalizeToolUsage(value: unknown): ToolUsageDTO {
  const data = record(value)
  return {
    toolName: String(data.tool_name ?? data.toolName ?? ''),
    serviceName: String(data.service_name ?? data.serviceName ?? ''),
    callCount: Number(data.call_count ?? data.callCount ?? 0),
    successCount: Number(data.success_count ?? data.successCount ?? 0),
    failureCount: Number(data.failure_count ?? data.failureCount ?? 0),
    successRate: Number(data.success_rate ?? data.successRate ?? 0),
    latencyMs: Number(data.latency_ms ?? data.latencyMs ?? 0),
  }
}

function normalizeActivity(value: unknown): DashboardActivityDTO {
  const data = record(value)
  return {
    date: String(data.date ?? ''),
    label: String(data.label ?? data.date ?? ''),
    modelCalls: Number(data.model_calls ?? data.modelCalls ?? 0),
    toolCalls: Number(data.tool_calls ?? data.toolCalls ?? 0),
    taskCount: Number(data.task_count ?? data.taskCount ?? 0),
    tokenCount: Number(data.token_count ?? data.tokenCount ?? 0),
  }
}

function normalizeInsight(value: unknown): DashboardInsightDTO {
  const data = record(value)
  return {
    label: String(data.label ?? ''),
    value: (data.value as number | string | undefined) ?? '',
    unit: String(data.unit ?? ''),
    tone: String(data.tone ?? ''),
  }
}

function normalizeEvent(value: unknown): DashboardEventDTO {
  const data = record(value)
  return {
    eventType: String(data.event_type ?? data.eventType ?? ''),
    title: String(data.title ?? ''),
    detail: String(data.detail ?? ''),
    status: String(data.status ?? ''),
    createdAt: (data.created_at as string | null | undefined) ?? (data.createdAt as string | null | undefined) ?? null,
  }
}

function normalizeSnapshot(value: unknown): DashboardSnapshotDTO {
  const data = record(value)
  return {
    generatedAt: String(data.generated_at ?? data.generatedAt ?? ''),
    range: record(data.range),
    overview: normalizeOverview(data.overview),
    modelUsage: list(data.model_usage ?? data.modelUsage).map(normalizeModelUsage),
    taskUsage: list(data.task_usage ?? data.taskUsage).map(normalizeTaskUsage),
    toolUsage: list(data.tool_usage ?? data.toolUsage).map(normalizeToolUsage),
    activity: list(data.activity).map(normalizeActivity),
    insights: list(data.insights).map(normalizeInsight),
    events: list(data.events).map(normalizeEvent),
  }
}

export async function getDashboardOverview(days = 30) {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/dashboard/overview', { params: { days } })
  return normalizeOverview(response.data.data)
}

export async function getDashboardModelUsage(days = 30) {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/dashboard/model-usage', { params: { days } })
  return list(response.data.data).map(normalizeModelUsage)
}

export async function getDashboardTaskUsage(days = 30) {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/dashboard/task-usage', { params: { days } })
  return list(response.data.data).map(normalizeTaskUsage)
}

export async function getDashboardToolUsage(days = 30) {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/dashboard/tool-usage', { params: { days } })
  return list(response.data.data).map(normalizeToolUsage)
}

export async function getDashboardSnapshot(days = 7) {
  const response = await apiClient.get<ApiEnvelope<unknown>>('/dashboard/snapshot', { params: { days } })
  return normalizeSnapshot(response.data.data)
}

export async function createDashboardSnapshot(days = 7) {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/dashboard/snapshot', null, { params: { days } })
  return normalizeSnapshot(response.data.data)
}
