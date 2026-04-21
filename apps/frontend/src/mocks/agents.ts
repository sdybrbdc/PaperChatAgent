import type { WorkflowNodeDTO, WorkflowSideCardDTO } from '../types/agents'

export const MOCK_WORKFLOW_NODES: WorkflowNodeDTO[] = [
  {
    id: 'node-search',
    title: '1. 搜索节点',
    description: '将自然语言需求整理成检索条件，连接 arXiv 与上传资料。',
  },
  {
    id: 'node-reading',
    title: '2. 阅读节点',
    description: '优先解析摘要，可获取全文时继续提取数据集、方法和结果。',
  },
  {
    id: 'node-analysis',
    title: '3. 分析节点',
    description: '对论文进行主题分组、方法比对，并形成后续问答语境。',
  },
  {
    id: 'node-writing',
    title: '4. 写作节点',
    description: '作为后续阶段预留能力，V1 只保留流程位置，不承诺正式报告输出。',
    tone: 'warn',
  },
  {
    id: 'node-report',
    title: '5. 报告节点',
    description: 'V1 不把综述报告生成作为主交付物，报告能力在未来阶段展开。',
    tone: 'warn',
  },
  {
    id: 'node-return',
    title: '6. 回流问答',
    description: '把结果沉淀为主题探索包，并在后续问答中提供带引用依据的回答。',
    tone: 'accent',
  },
]

export const MOCK_WORKFLOW_RAIL: WorkflowSideCardDTO[] = [
  {
    title: '当前模式',
    lines: ['预置研究智能体', 'LangGraph 主编排，后续可扩展更多节点配置。'],
  },
  {
    title: '节点说明',
    lines: [
      '搜索 / 阅读 / 分析 是 V1 主链路。',
      '写作 / 报告 作为后续规划展示。',
      '最终目标是把结果回流成可继续追问的研究上下文。',
    ],
  },
]
