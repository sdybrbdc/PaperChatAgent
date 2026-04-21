export interface ResearchTaskDTO {
  id: string
  title: string
  subtitle: string
  status: 'queued' | 'running' | 'completed' | 'failed'
}

export interface TaskMetricDTO {
  key: string
  label: string
  value: string
  tone: 'warning' | 'brand' | 'success' | 'danger'
}

export interface TaskDetailCardDTO {
  title: string
  lines: string[]
}
