import type { ResearchTaskDTO, TaskDetailCardDTO, TaskMetricDTO } from '../types/tasks'
import { apiClient } from '../utils/http'

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
  request_id: string
}

export async function getTasksOverview() {
  const response = await apiClient.get<
    ApiEnvelope<{
      items: Array<Record<string, unknown>>
    }>
  >('/tasks')

  const tasks: ResearchTaskDTO[] = response.data.data.items.map((item) => ({
    id: String(item.id ?? ''),
    title: String(item.title ?? ''),
    subtitle: String(item.detail ?? ''),
    status: (item.status as 'queued' | 'running' | 'completed' | 'failed') ?? 'queued',
  }))

  const counts = {
    queued: tasks.filter((task) => task.status === 'queued').length,
    running: tasks.filter((task) => task.status === 'running').length,
    completed: tasks.filter((task) => task.status === 'completed').length,
    failed: tasks.filter((task) => task.status === 'failed').length,
  }

  const metrics: TaskMetricDTO[] = [
    { key: 'queued', label: '排队中', value: String(counts.queued), tone: 'warning' },
    { key: 'running', label: '执行中', value: String(counts.running), tone: 'brand' },
    { key: 'completed', label: '已完成', value: String(counts.completed), tone: 'success' },
    { key: 'failed', label: '失败', value: String(counts.failed), tone: 'danger' },
  ]

  const rail: TaskDetailCardDTO[] = [
    {
      title: '任务流说明',
      lines: ['任务页已切换为真实接口', '进度流通过 SSE 订阅', '当前任务列表来自 backend /tasks'],
    },
  ]

  return { metrics, tasks, rail }
}
