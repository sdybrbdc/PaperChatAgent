import type {
  ChatSessionDTO,
  ConversationHistoryGroup,
  InboxConversationDTO,
  MessageDTO,
  TaskSuggestionDTO,
} from '../types/chat'

export const MOCK_INBOX_CONVERSATION: InboxConversationDTO = {
  id: 'inbox-1',
  title: '默认收件箱会话',
  status: 'active',
  summary: '正在讨论：论文相关 Agent 的研究范围',
}

export const MOCK_CHAT_SESSION: ChatSessionDTO = {
  id: 'chat-session-1',
  title: '默认聊天页',
  scope: 'inbox',
}

export const MOCK_HISTORY_GROUPS: ConversationHistoryGroup[] = [
  {
    id: 'history-inbox',
    title: '默认收件箱会话',
    subtitle: '正在讨论：论文相关 Agent 的研究范围',
    type: 'inbox',
  },
  {
    id: 'workspace-1',
    title: '工作区：多智能体论文问答',
    items: ['会话：主题探索与任务确认', '会话：引用问答与结果追问'],
    type: 'workspace',
  },
  {
    id: 'workspace-2',
    title: '工作区：RAG for Papers',
    items: ['会话：论文检索与知识库整理'],
    type: 'workspace',
  },
  {
    id: 'workspace-3',
    title: '工作区：Agentic Survey',
    items: ['会话：综述结构与研究脉络'],
    type: 'workspace',
  },
  {
    id: 'workspace-4',
    title: '工作区：多模态论文理解',
    items: ['会话：视觉模型评估', '会话：表格与图像解析'],
    type: 'workspace',
  },
  {
    id: 'workspace-5',
    title: '工作区：论文推荐系统',
    items: ['会话：候选召回策略', '会话：用户画像与排序'],
    type: 'workspace',
  },
  {
    id: 'workspace-6',
    title: '工作区：长文本 RAG',
    items: ['会话：切片策略', '会话：引用证据定位'],
    type: 'workspace',
  },
  {
    id: 'workspace-7',
    title: '工作区：科研助手产品设计',
    items: ['会话：用户旅程', '会话：工作台布局', '会话：登录注册体验'],
    type: 'workspace',
  },
  {
    id: 'workspace-8',
    title: '工作区：AutoGen 协作模式',
    items: ['会话：节点内代理角色', '会话：HITL 审查机制'],
    type: 'workspace',
  },
  {
    id: 'workspace-9',
    title: '工作区：LangGraph 状态机',
    items: ['会话：状态定义', '会话：条件边设计', '会话：错误恢复'],
    type: 'workspace',
  },
  {
    id: 'workspace-10',
    title: '工作区：知识库与私有库',
    items: ['会话：全局知识库复用', '会话：私有库绑定规则'],
    type: 'workspace',
  },
  {
    id: 'workspace-11',
    title: '工作区：报告生成与回流问答',
    items: ['会话：章节写作', '会话：报告工件', '会话：结果回流'],
    type: 'workspace',
  },
  {
    id: 'workspace-12',
    title: '工作区：论文聚类与趋势分析',
    items: ['会话：KMeans 聚类', '会话：趋势识别', '会话：热点总结'],
    type: 'workspace',
  },
  {
    id: 'workspace-13',
    title: '工作区：引用依据系统',
    items: ['会话：paper 级引用', '会话：paragraph 级定位'],
    type: 'workspace',
  },
  {
    id: 'workspace-14',
    title: '工作区：前端静态实现',
    items: ['会话：Mock 登录', '会话：Pinia 状态组织', '会话：页面空态'],
    type: 'workspace',
  },
]

export const MOCK_MESSAGES: MessageDTO[] = [
  {
    id: 'msg-1',
    role: 'assistant',
    messageType: 'chat',
    content:
      '你想研究哪个方向？如果还没想清楚，可以先说你的兴趣、已有论文，或者你希望这个 Agent 最终帮你完成什么。',
    createdAt: '2026-04-22T09:00:00+08:00',
  },
  {
    id: 'msg-2',
    role: 'user',
    messageType: 'chat',
    content:
      '我想做一个论文相关的 Agent，面向科研人员和学生，但现在还没完全想清楚边界。',
    createdAt: '2026-04-22T09:00:10+08:00',
  },
  {
    id: 'msg-3',
    role: 'assistant',
    messageType: 'chat',
    content:
      '我先帮你把问题收束成一个可执行的研究任务：\n1. 聚焦“主题级论文问答助手”而不是直接写综述\n2. 资料入口采用 arXiv + 用户上传 PDF\n3. 研究结果要沉淀为可继续问答的主题探索包',
    createdAt: '2026-04-22T09:00:30+08:00',
  },
]

export const MOCK_TASK_SUGGESTION: TaskSuggestionDTO = {
  title: 'AI 建议的研究任务',
  topic: '面向科研人员和学生的主题级论文问答工作台',
  sources: 'arXiv + 用户上传 PDF',
  outputs: '研究工作区、研究任务、主题探索包、带引用依据的问答上下文',
  nextStep: '用户确认关键词、时间范围和上传资料，再启动后台研究流程',
  statusLabel: '可创建工作区',
}

export const MOCK_CHAT_RAIL = [
  {
    title: '研究任务确认面板',
    lines: ['会话：默认收件箱会话', '状态：研究方向已初步明确', '下一步：确认后创建工作区'],
  },
  {
    title: '建议任务配置',
    lines: [
      '主题：论文相关 Agent',
      '关键词：多智能体、论文问答、工作区',
      '来源：arXiv + 用户 PDF',
      '引用：默认论文级，可扩展细粒度',
      '产物：主题探索包 + 问答上下文',
    ],
  },
  {
    title: '预置研究智能体工作流',
    lines: [
      '1. 搜索节点：收束需求与检索条件',
      '2. 阅读节点：解析摘要与全文信息',
      '3. 分析节点：形成主题脉络与分组',
      '4. 写作节点：作为后续阶段预留能力',
      '5. 报告节点：V1 不作为正式交付',
      '6. 回流问答：沉淀为主题探索包',
    ],
  },
  {
    title: '已上传资料',
    lines: ['paper-agent-notes.pdf', '等待绑定到研究任务'],
  },
]
