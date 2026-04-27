export interface DashboardMetricPointDTO {
  label: string
  value: number
  extra?: Record<string, unknown>
}

export interface DashboardOverviewDTO {
  modelCallCount: number
  inputTokenCount: number
  outputTokenCount: number
  recentTaskCount: number
  activeTaskCount: number
  failedTaskCount: number
  toolCallCount: number
  taskStatusDistribution: DashboardMetricPointDTO[]
}

export interface ModelUsageDTO {
  providerName: string
  modelName: string
  callCount: number
  inputTokens: number
  outputTokens: number
  latencyMs: number
}

export interface TaskUsageDTO {
  status: string
  count: number
  averageProgress: number
}

export interface ToolUsageDTO {
  toolName: string
  serviceName: string
  callCount: number
  successCount: number
  failureCount: number
  latencyMs: number
}

export interface DashboardEventDTO {
  eventType: string
  title: string
  detail: string
  status: string
  createdAt: string | null
}

export interface DashboardSnapshotDTO {
  generatedAt: string
  range: Record<string, unknown>
  overview: DashboardOverviewDTO
  modelUsage: ModelUsageDTO[]
  taskUsage: TaskUsageDTO[]
  toolUsage: ToolUsageDTO[]
  events: DashboardEventDTO[]
}
