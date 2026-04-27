import type {
  DashboardEventDTO,
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
    recentTaskCount: Number(data.recent_task_count ?? data.recentTaskCount ?? 0),
    activeTaskCount: Number(data.active_task_count ?? data.activeTaskCount ?? 0),
    failedTaskCount: Number(data.failed_task_count ?? data.failedTaskCount ?? 0),
    toolCallCount: Number(data.tool_call_count ?? data.toolCallCount ?? 0),
    taskStatusDistribution,
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
    latencyMs: Number(data.latency_ms ?? data.latencyMs ?? 0),
  }
}

function normalizeTaskUsage(value: unknown): TaskUsageDTO {
  const data = record(value)
  return {
    status: String(data.status ?? ''),
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
    latencyMs: Number(data.latency_ms ?? data.latencyMs ?? 0),
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

export async function createDashboardSnapshot(days = 7) {
  const response = await apiClient.post<ApiEnvelope<unknown>>('/dashboard/snapshot', null, { params: { days } })
  return normalizeSnapshot(response.data.data)
}
