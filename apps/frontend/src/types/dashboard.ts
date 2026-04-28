export interface DashboardMetricPointDTO {
  label: string
  value: number
  extra?: Record<string, unknown>
}

export interface DashboardOverviewDTO {
  modelCallCount: number
  inputTokenCount: number
  outputTokenCount: number
  tokenCount: number
  recentTaskCount: number
  activeTaskCount: number
  failedTaskCount: number
  toolCallCount: number
  taskStatusDistribution: DashboardMetricPointDTO[]
  averageLatencyMs: number
  taskCompletionRate: number
  taskFailureRate: number
}

export interface ModelUsageDTO {
  providerName: string
  modelName: string
  callCount: number
  inputTokens: number
  outputTokens: number
  totalTokens: number
  successCount: number
  errorCount: number
  successRate: number
  latencyMs: number
  routeKey: string
}

export interface TaskUsageDTO {
  status: string
  currentNode: string
  count: number
  averageProgress: number
}

export interface ToolUsageDTO {
  toolName: string
  serviceName: string
  callCount: number
  successCount: number
  failureCount: number
  successRate: number
  latencyMs: number
}

export interface DashboardActivityDTO {
  date: string
  label: string
  modelCalls: number
  toolCalls: number
  taskCount: number
  tokenCount: number
}

export interface DashboardInsightDTO {
  label: string
  value: number | string
  unit: 'ratio' | 'ms' | 'text' | string
  tone: string
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
  activity: DashboardActivityDTO[]
  insights: DashboardInsightDTO[]
  events: DashboardEventDTO[]
}
