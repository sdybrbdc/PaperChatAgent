import type { ResearchTaskDTO, TaskDetailCardDTO, TaskMetricDTO } from '../types/tasks'

export const MOCK_TASK_METRICS: TaskMetricDTO[] = [
  { key: 'queued', label: '待执行', value: '02', tone: 'warning' },
  { key: 'running', label: '执行中', value: '01', tone: 'brand' },
  { key: 'completed', label: '已完成', value: '06', tone: 'success' },
  { key: 'failed', label: '失败', value: '00', tone: 'danger' },
]

export const MOCK_TASKS: ResearchTaskDTO[] = [
  {
    id: 'task-1024',
    title: '任务 #1024 · 论文相关 Agent 主题探索',
    subtitle: '当前步骤：阅读节点 · 已完成检索与下载，正在解析摘要和全文。',
    status: 'running',
  },
  {
    id: 'task-1023',
    title: '任务 #1023 · RAG for Papers 工作区知识库整理',
    subtitle: '当前步骤：已完成 · 已生成主题探索包，并可继续在聊天页追问。',
    status: 'completed',
  },
  {
    id: 'task-1022',
    title: '任务 #1022 · 上传 PDF 预处理与引用锚点生成',
    subtitle: '当前步骤：待执行 · 等待用户确认是否并入当前前研究工作区。',
    status: 'queued',
  },
]

export const MOCK_TASK_RAIL: TaskDetailCardDTO[] = [
  {
    title: '选中任务详情',
    lines: ['任务 #1024', '工作区：多智能体论文问答', '状态：执行中 · 当前节点：阅读'],
  },
  {
    title: '步骤进度',
    lines: ['1. 搜索节点：已完成', '2. 阅读节点：执行中', '3. 分析节点：待执行', '4. 回流问答：待执行'],
  },
  {
    title: '输出结果',
    lines: ['预计产物：主题探索包、引用片段、可继续问答上下文。'],
  },
]
