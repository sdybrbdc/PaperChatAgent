import type { KnowledgeBaseDTO, KnowledgeSideCardDTO } from '../types/knowledge'

export const MOCK_GLOBAL_KB: KnowledgeBaseDTO = {
  id: 'kb-global',
  title: '账号内全局知识库',
  description: '跨工作区复用论文、摘要和结构化解析结果。',
  files: [
    {
      id: 'gf-1',
      title: 'Retrieval-Augmented Generation for Scientific Papers',
      subtitle: 'arXiv · 已解析',
    },
    {
      id: 'gf-2',
      title: 'Agentic Survey Systems Overview',
      subtitle: '上传 PDF · 待绑定工作区',
    },
    {
      id: 'gf-3',
      title: 'Multi-Agent Literature QA Baseline',
      subtitle: 'arXiv · 已被 2 个工作区引用',
    },
  ],
}

export const MOCK_PRIVATE_KB: KnowledgeBaseDTO = {
  id: 'kb-private',
  title: '工作区私有知识库',
  description: '当前工作区：多智能体论文问答。这里存放仅服务于本主题的临时材料与补充文件。',
  files: [
    {
      id: 'pf-1',
      title: 'paper-agent-notes.pdf',
      subtitle: '来源：用户上传 · 状态：已入库，等待关联任务',
    },
    {
      id: 'pf-2',
      title: 'topic-seed-keywords.md',
      subtitle: '来源：工作区补充 · 状态：仅当前主题可见',
    },
  ],
}

export const MOCK_KNOWLEDGE_RAIL: KnowledgeSideCardDTO[] = [
  {
    title: '库结构',
    lines: ['全局知识库：可跨工作区复用', '私有知识库：仅当前主题使用'],
  },
  {
    title: '上传任务',
    lines: ['最近上传：1 个 PDF，1 个 markdown', '待处理：paper-agent-notes.pdf', '建议：处理后挂接到工作区私有库'],
  },
  {
    title: '当前工作区引用',
    lines: ['工作区：多智能体论文问答', '已引用：3 篇论文，2 个私有文件'],
  },
]
