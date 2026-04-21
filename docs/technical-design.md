# PaperChatAgent 技术方案文档

## 1. 文档目标

本文档用于冻结 V1 的技术选型、接口风格、配置方式和运行边界，达到“实现者读完即可搭项目骨架”的粒度。

## 2. 技术基线

### 2.1 前端

- 框架：Vue 3
- 构建工具：Vite
- 包管理：pnpm
- 路由：Vue Router
- 状态管理：Pinia
- UI 组件库：Element Plus
- 目标：构建默认聊天页、工作区视图、知识库页、智能体页、后台任务页

说明：

- 由于项目基于 Vue 3，组件库采用 `Element Plus`，而不是旧版 `Element UI`
- `Pinia` 作为当前项目的默认状态管理方案，不再采用纯局部状态拼装页面

### 2.2 后端

- 框架：FastAPI
- 风格：异步 API 服务
- 分层方式：Pydantic / SQLModel 风格分层
- 目标：提供 REST API、SSE 流、认证、工作区/任务/知识库资源管理

### 2.3 队列与任务执行

- 队列：Redis
- 任务执行器：独立 worker 进程
- 目标：承接检索、下载、解析、建索引和主题探索等长任务

### 2.4 数据与存储

- 关系数据库：MySQL
- 向量数据库：ChromaDB
- 对象存储：MinIO

### 2.5 工作流与模型

- 工作流编排：LangGraph + AutoGen
- 模型接入：Provider abstraction + LangChain configuration
- 预留多模型路由：
  - conversation
  - tool_call
  - reasoning
  - embedding
  - rerank

## 3. API 风格

### 3.1 资源接口

V1 后端采用 `REST` 作为主资源接口风格。原因：

- 与当前工作台型产品形态一致
- 更适合用户、工作区、任务、知识、会话等资源建模
- 实现和调试成本低于 GraphQL

### 3.2 流式与实时接口

V1 使用 `SSE` 处理以下两类实时场景：

- 聊天输出流
- 后台任务进度流

不使用 WebSocket 作为首选协议，原因：

- 当前交互主要是单向事件推送
- SSE 更容易与 FastAPI 集成
- 对前端调试和部署代理更友好

## 3.3 前后端数据契约

前端和后端必须围绕统一 DTO/VO 契约开发，不能让前端自行拼装后端返回结构。

建议原则：

- 后端返回稳定的页面消费对象，不让前端自行猜字段
- 前端 Pinia store 直接消费 DTO，不在组件里临时重组
- 消息、任务、工作区、知识库等核心资源统一使用 `id + status + timestamps + metadata` 的基础结构

推荐首批对齐的数据对象如下：

| 前端类型 | 后端资源 | 主要来源表 | 说明 |
|---|---|---|---|
| `CurrentUserDTO` | `/me` | `users` | 当前用户信息 |
| `InboxConversationDTO` | `/conversations/inbox` | `inbox_conversations` | 默认收件箱会话 |
| `ChatSessionDTO` | `/conversations/*` | `chat_sessions` | 会话容器 |
| `MessageDTO` | `/conversations/{id}/messages` | `messages` | 聊天消息 |
| `TaskSuggestionDTO` | `messages.message_type=task_suggestion` | `messages` | 任务建议消息 |
| `ResearchWorkspaceDTO` | `/workspaces/*` | `research_workspaces` | 工作区信息 |
| `KnowledgeBaseDTO` | `/knowledge` | `knowledge_bases` | 知识库容器 |
| `KnowledgeFileDTO` | `/knowledge/files/*` | `knowledge_files` | 文件/论文资源 |
| `ResearchTaskDTO` | `/tasks/*` | `research_tasks` | 任务主对象 |
| `WorkflowNodeDTO` | `/agents/workflows/{id}/nodes` | `workflow_node_runs` | 节点状态 |
| `TopicExplorationPackageDTO` | 工作区问答增强 | `topic_exploration_packages` | 主题探索包 |
| `CitationEvidenceDTO` | 消息引用依据 | `citation_evidences` | 引用详情 |
| `ReportArtifactDTO` | `/tasks/{id}/report` | `report_artifacts` | 报告产物 |

前端组件层不应直接依赖数据库字段名，而应依赖 DTO 名称。

## 4. 聊天层技术路线

聊天层明确参考 AgentChat 的实现方式，但按 PaperChatAgent 的业务语义重新组织资源。

固定设计：

- 使用 LangChain 作为聊天模型与 RAG 编排基础层
- 模型实例通过 LangChain `ChatOpenAI` 风格对象统一创建
- 保留 AgentChat 的多模型配置思想：
  - `conversation_model`
  - `tool_call_model`
  - `reasoning_model`
  - `embedding_model`
  - `rerank_model`
- RAG 能力参考 AgentChat 的组织方式：
  - 查询改写
  - 混合检索
  - 重排序
  - 注入问答上下文

聊天服务建议分层：

- `chat service`
- `langchain model manager`
- `rag handler`
- `stream service`

### 4.2 前端聊天实现细节

默认聊天页前端建议拆为：

- `ChatPage`
  - 页面容器，负责布局和路由入口
- `ConversationSidebar`
  - 左侧工作区/会话分组
- `MessageList`
  - 消息列表
- `Composer`
  - 输入框、上传按钮、发送按钮
- `TaskSuggestionCard`
  - 结构化任务建议渲染
- `TaskConfirmDrawer` 或 `TaskConfirmPanel`
  - 任务确认面板

Pinia 建议拆分以下 store：

- `authStore`
  - 当前用户、登录态、登出
- `workspaceStore`
  - 工作区列表、当前工作区、分享信息
- `conversationStore`
  - 收件箱会话、当前会话、消息列表、SSE 流
- `knowledgeStore`
  - 知识库、文件上传状态、绑定关系
- `taskStore`
  - 任务列表、任务详情、任务进度流
- `uiStore`
  - 抽屉、面板、主题、局部页面状态

### 4.3 Element Plus 使用原则

组件实现建议基于 Element Plus，优先使用现成组件而不是手搓基础交互：

- 表单：`el-form`
- 输入：`el-input`
- 选择器：`el-select`
- 表格：`el-table`
- 抽屉/弹窗：`el-drawer` / `el-dialog`
- Tabs：`el-tabs`
- 菜单：`el-menu`
- 上传：`el-upload`
- 消息反馈：`el-message` / `el-notification`
- 加载态：`el-skeleton` / `el-loading`

说明：

- 工作台类产品更适合稳健的业务组件，不建议从一开始就追求大量自定义基础控件
- 设计稿中的布局、配色、间距仍然由项目主题层统一覆盖，不直接照搬 Element 默认视觉

### 4.4 聊天与知识检索关系

- 默认收件箱会话：优先使用轻量聊天与任务建议
- 工作区问答：优先使用工作区绑定的主题探索包和知识库
- 报告问答：支持在完整工作流结束后围绕报告和引用继续追问

## 5. 认证方案

认证参考 AgentChat 当前做法：

- JWT 支持 `cookies + headers`
- Web 场景默认采用 `HttpOnly Cookie`
- 保留 Header 传 token 的兼容能力

V1 推荐策略：

- 登录成功后，服务端写入 HttpOnly Cookie
- 前端以浏览器会话为主，不在页面逻辑中广泛暴露原始 token
- 对需要兼容脚本或特殊调用的场景，允许 Header 形式

V1 不做：

- OAuth 第三方登录
- 多角色权限系统
- 细粒度 RBAC

## 6. 配置策略

### 6.1 配置文件

V1 配置采用：

- `config.example.yaml`：示例配置
- `config.yaml`：本地实际配置

YAML 中至少包含以下配置段：

- `server`
- `mysql`
- `redis`
- `storage`
- `vector_db`
- `multi_models`
- `search`

### 6.2 地址示例

配置示例以本机地址为默认例子，例如：

```yaml
server:
  host: "127.0.0.1"
  port: 8000

mysql:
  endpoint: "mysql+pymysql://root:password@127.0.0.1:3306/paperchatagent"
  async_endpoint: "mysql+aiomysql://root:password@127.0.0.1:3306/paperchatagent"

redis:
  endpoint: "redis://127.0.0.1:6379"

storage:
  mode: "minio"
  minio:
    endpoint: "127.0.0.1:9000"
    access_key_id: "minioadmin"
    access_key_secret: "minioadmin"
    bucket_name: "paperchatagent"

multi_models:
  conversation_model:
    api_key: "your-key"
    base_url: "https://your-openai-compatible-endpoint/v1"
    model_name: "gpt-4o-mini"
  tool_call_model:
    api_key: "your-key"
    base_url: "https://your-openai-compatible-endpoint/v1"
    model_name: "gpt-4o-mini"
  reasoning_model:
    api_key: "your-key"
    base_url: "https://your-reasoning-endpoint/v1"
    model_name: "deepseek-reasoner"
  embedding_model:
    api_key: "your-key"
    base_url: "https://your-embedding-endpoint/v1"
    model_name: "text-embedding-3-large"
  rerank_model:
    api_key: "your-key"
    base_url: "https://your-rerank-endpoint/v1"
    model_name: "rerank-model"
```

## 7. 工作流实现路线

### 7.1 总体策略

工作流层明确采用 `AutoGen + LangGraph` 双栈：

- `LangGraph`：负责全局状态机、节点顺序、条件流转、错误处理
- `AutoGen`：负责节点内部智能体协作、人工审查代理、并行写作协作

### 7.2 完整工作流节点

工作流完整吸收 Paper-Agent 的节点设计：

1. `search_agent_node`
2. `reading_agent_node`
3. `analyse_agent_node`
4. `writing_agent_node`
5. `report_agent_node`

### 7.3 节点内智能体

参考 Paper-Agent，关键节点内部能力如下：

- `search_agent_node`
  - `search_agent`
  - `userProxyAgent`
- `reading_agent_node`
  - 并行 `read_agent`
- `analyse_agent_node`
  - `PaperClusterAgent`
  - `DeepAnalyseAgent`
  - `GlobalanalyseAgent`
- `writing_agent_node`
  - `writing_director_agent`
  - `writing_agent`
  - `retrieval_agent`
  - `review_agent`
- `report_agent_node`
  - `report_agent`

### 7.4 与当前项目的融合方式

PaperChatAgent 不把 Paper-Agent 当成独立外挂模块，而是把其工作流概念融入当前项目模型：

- 工作流输入来自聊天页与工作区上下文
- 工作流中间结果写入知识库与任务状态
- 工作流输出写入主题探索包、报告工件和问答上下文
- 前端通过任务页与聊天页消费这些结果

## 8. 本地运行边界

### 8.1 支持两种方式

V1 文档同时支持：

- Docker Compose 启动依赖服务
- 本机直连方式配置本地服务

推荐顺序：

- 优先使用 Docker Compose 起 MySQL / Redis / MinIO / Chroma
- 如果开发者本地已经有常驻服务，则允许通过 YAML 直连

### 8.2 不纳入本轮的内容

- 生产部署编排
- 云资源配置
- CI/CD
- 日志采集与告警平台

## 9. 模型接入策略

### 9.1 Provider abstraction

从 V1 开始保留模型抽象层，不把业务代码写死到单一供应商。原因：

- 对话、工具调用、推理、Embedding、Rerank 的最优模型通常不同
- 后续切换 OpenAI 兼容服务或私有部署时成本更低
- 便于测试不同组合

### 9.2 路由建议

至少定义以下逻辑模型槽位：

- `conversation_model`
- `tool_call_model`
- `reasoning_model`
- `embedding_model`
- `rerank_model`

### 9.3 Provider 层职责

- 接收统一配置
- 对外暴露一致调用接口
- 处理不同服务商的 base_url / headers / auth 差异

Provider 层不负责：

- 工作区语义
- 任务调度
- 业务状态管理

## 10. 首批后端目录建议

```text
apps/backend/
└── paperchat/
    ├── main.py
    ├── settings.py
    ├── config.example.yaml
    ├── api/
    │   ├── responses/
    │   ├── errcode/
    │   ├── router.py
    │   └── v1/
    ├── auth/
    ├── middleware/
    ├── core/
    │   ├── callbacks/
    │   └── runtime/
    ├── services/
    │   ├── chat/
    │   ├── workspace/
    │   ├── knowledge/
    │   ├── task/
    │   ├── rag/
    │   ├── rewrite/
    │   └── storage/
    ├── database/
    │   ├── models/
    │   └── dao/
    ├── workflows/
    │   ├── graph/
    │   ├── nodes/
    │   └── agents/
    ├── tasks/
    ├── storage/
    ├── schemas/
    └── providers/
```

各目录职责：

- `api/`：REST 与 SSE 路由
- `api/responses/`：统一响应对象
- `api/errcode/`：错误码定义
- `auth/`：JWT 认证和登录态逻辑
- `middleware/`：Trace ID、CORS、白名单、审计中间件
- `core/`：运行时公共能力和回调
- `services/`：业务服务层
- `services/chat/`：聊天服务
- `services/workspace/`：工作区服务
- `services/knowledge/`：知识库服务
- `services/task/`：任务服务
- `services/rag/`：RAG 检索服务
- `services/rewrite/`：查询改写
- `services/storage/`：对象存储服务
- `database/`：数据模型与数据访问层
- `workflows/graph/`：LangGraph 图定义
- `workflows/nodes/`：search/reading/analyse/writing/report 节点
- `workflows/agents/`：AutoGen 代理定义
- `tasks/`：Worker 任务执行逻辑
- `storage/`：MinIO 与对象存储抽象
- `providers/`：LangChain / 模型供应商抽象层

## 11. 首批前端目录建议

```text
apps/frontend/
├── src/
│   ├── apis/
│   ├── components/
│   │   ├── chat/
│   │   ├── workspace/
│   │   ├── knowledge/
│   │   ├── agents/
│   │   └── tasks/
│   ├── pages/
│   │   ├── login/
│   │   ├── chat/
│   │   ├── workspace/
│   │   ├── knowledge/
│   │   ├── agents/
│   │   └── tasks/
│   ├── router/
│   ├── stores/
│   ├── layouts/
│   ├── types/
│   └── utils/
├── package.json
├── pnpm-lock.yaml
└── vite.config.ts
```

前端目录补充说明：

- `apis/`：按资源拆分 API client
- `stores/`：Pinia store
- `types/`：前后端共享的前端 DTO 类型定义
- `layouts/`：工作台主布局、认证布局
- `components/`：页面级复用业务组件，而不是只放基础组件

## 12. 首批接口资源边界

### 12.1 Auth

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /me`

### 12.2 Inbox / Chat

- `GET /conversations/inbox`
- `GET /conversations/{id}/messages`
- `POST /conversations/{id}/messages`
- `GET /conversations/{id}/stream`

### 12.3 Workspace

- `POST /workspaces`
- `GET /workspaces`
- `GET /workspaces/{id}`
- `POST /workspaces/{id}/share-link`

### 12.4 Knowledge

- `GET /knowledge`
- `POST /knowledge/files/upload`
- `POST /knowledge/import/arxiv`
- `POST /knowledge/attach`

### 12.5 Task

- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{id}`
- `GET /tasks/{id}/events`
- `POST /tasks/{id}/retry`
- `GET /tasks/{id}/report`

### 12.6 Agent / Workflow

- `GET /agents/workflows`
- `GET /agents/workflows/{id}`
- `GET /agents/workflows/{id}/nodes`

## 13. 非目标

本轮技术方案不包括：

- 字段级数据库 migration 细节
- 正式生产部署方案
- 复杂多租户权限设计
- GraphQL / WebSocket 主体架构切换

## 14. 端到端实现流程详解

本节按真实业务顺序说明当前技术文档所要求的实现路径：

`注册 -> 登录 -> 默认聊天 -> 确定研究领域 -> 确认任务 -> 执行完整工作流 -> 回流问答`

### 14.1 注册

接口：

- `POST /auth/register`

建议请求体：

```json
{
  "email": "user@example.com",
  "password": "plain-password",
  "display_name": "alice"
}
```

后端行为：

1. 校验邮箱唯一性
2. 对密码做 hash
3. 创建 `users`
4. 创建该用户的 `inbox_conversations`
5. 创建默认 `chat_sessions`，其 `session_scope = inbox`

建议响应：

```json
{
  "user_id": "uuid",
  "inbox_conversation_id": "uuid",
  "default_session_id": "uuid"
}
```

实现约束：

- V1 不做邮箱验证码
- 注册成功后即可登录

### 14.2 登录

接口：

- `POST /auth/login`

后端行为：

1. 校验用户邮箱与密码
2. 签发 access / refresh JWT
3. 写入 HttpOnly Cookie
4. 创建 `user_sessions`

补充接口：

- `GET /me`
- `POST /auth/logout`

实现约束：

- `GET /me` 用于前端刷新登录态
- 登出时需要吊销或标记 `user_sessions.revoked_at`

### 14.3 打开默认聊天页

接口：

- `GET /conversations/inbox`
- `GET /conversations/{id}/messages`

后端行为：

1. 返回当前用户的 `inbox_conversations`
2. 返回默认收件箱下最近活跃的 `chat_sessions`
3. 返回该会话的消息历史

前端行为：

- 登录成功后默认进入聊天页
- 如果没有历史消息，则展示空白引导态

### 14.4 聊天确定研究领域

接口：

- `POST /conversations/{id}/messages`
- `GET /conversations/{id}/stream`

处理路径：

1. 前端提交用户消息
2. 后端写入一条 `messages(role=user, message_type=chat)`
3. Chat service 调用 LangChain conversation model
4. 若当前会话已绑定工作区，则额外走 RAG：
   - query rewrite
   - retrieval
   - rerank
   - context injection
5. 将 AI 回复流式返回前端
6. AI 回复完成后写入一条 `messages(role=assistant, message_type=chat 或 task_suggestion)`

此阶段目标：

- 帮用户把研究问题收束为可执行研究任务
- 允许用户上传 PDF 并参与上下文

### 14.5 上传论文 / 资料

接口：

- `POST /knowledge/files/upload`
- `POST /knowledge/import/arxiv`

建议策略：

- 用户第一次上传资料时，如果还没有账号级全局知识库，则自动创建一个 `scope = global` 的 `knowledge_bases`
- 上传成功后创建一条 `knowledge_files`
- 后续由 worker 负责解析与索引

如果上传发生在聊天过程中：

- 前端应把上传结果与当前 `chat_sessions` 关联显示
- 但资料主归属仍然是知识库，而不是消息表

### 14.6 AI 给出研究任务建议

此阶段不是单独页面，而是聊天结果中的一种结构化消息。

建议做法：

- AI 生成任务建议时，将 assistant 消息写成：
  - `message_type = task_suggestion`
  - `content_json` 中包含：
    - topic
    - keywords
    - date_range
    - selected_sources
    - selected_files

这样前端可以直接渲染确认面板，而不是靠纯文本解析。

### 14.7 用户确认并创建研究任务

接口：

- `POST /tasks`

建议请求体：

```json
{
  "source_session_id": "uuid",
  "workspace_name": "多智能体论文问答",
  "topic": "面向科研人员和学生的论文问答工作台",
  "keywords": ["多智能体", "论文问答", "工作区"],
  "source_config": {
    "arxiv": true,
    "uploaded_files": ["knowledge-file-id-1"]
  }
}
```

后端行为：

1. 若未指定已有工作区，则创建 `research_workspaces`
2. 创建 `research_tasks`
3. 创建 `workflow_runs`
4. 初始化 5 条 `workflow_node_runs`
5. 若任务需要引用知识库或文件，则创建 `workspace_knowledge_links`
6. 将任务投递到 Redis

建议默认节点顺序：

1. `search_agent_node`
2. `reading_agent_node`
3. `analyse_agent_node`
4. `writing_agent_node`
5. `report_agent_node`

### 14.8 执行完整工作流

执行端：

- `apps/worker`

工作流职责拆分：

- LangGraph：
  - 维护全局状态对象
  - 负责节点跳转
  - 负责条件边与错误边
- AutoGen：
  - 节点内部智能体协作
  - `userProxyAgent`
  - `read_agent`
  - `PaperClusterAgent`
  - `DeepAnalyseAgent`
  - `GlobalanalyseAgent`
  - `writing_agent`
  - `retrieval_agent`
  - `review_agent`
  - `report_agent`

每个节点完成时需要：

1. 更新 `workflow_node_runs.status`
2. 更新 `research_tasks.current_node`
3. 更新 `research_tasks.progress_percent`
4. 将必要的中间结果写回数据库

### 14.9 各节点落库要求

#### `search_agent_node`

- 写入或更新：
  - `workflow_node_runs`
  - `research_papers`
- 如果需要人工确认：
  - 状态保持在 `pending review` 的扩展态可落在 `trace_json` 或 `metadata_json`

#### `reading_agent_node`

- 写入或更新：
  - `extracted_papers`
  - `knowledge_chunks`
  - `knowledge_files.parser_status`
  - `knowledge_files.index_status`

#### `analyse_agent_node`

- 写入或更新：
  - `analysis_clusters`
  - `analysis_cluster_papers`
  - `analysis_reports`

#### `writing_agent_node`

- 写入或更新：
  - `writing_outlines`
  - `writing_sections`

#### `report_agent_node`

- 写入或更新：
  - `report_artifacts`
  - `topic_exploration_packages`

### 14.10 任务进度推送

接口：

- `GET /tasks/{id}/events`

SSE 事件建议至少包含：

- `task.created`
- `task.node.started`
- `task.node.completed`
- `task.node.failed`
- `task.completed`
- `task.failed`

前端任务页与聊天页都可订阅这条流。

### 14.11 工作流完成后的回流问答

任务完成后，聊天不应重新从零开始，而应切换到“工作区增强问答”模式。

实现方式：

1. 在工作区绑定 `topic_exploration_packages`
2. 工作区问答时优先检索：
   - `topic_exploration_packages`
   - `analysis_reports`
   - `writing_sections`
   - `report_artifacts`
   - `knowledge_chunks`
3. 回答生成后写入：
   - `messages`
   - `citation_evidences`

### 14.12 当前需要你确认的实现细节

基于当前文档，我认为以下实现默认值最合适，除非你后续明确改动：

1. 注册成功后自动创建：
   - `inbox_conversations`
   - 一个默认 `chat_sessions`
2. 用户第一次上传文件时自动创建账号级全局知识库
3. `POST /tasks` 若不指定现有工作区，则自动创建新工作区
4. 完整工作流默认执行到 `report_agent_node`，而不是停在分析节点

如果你认可这 4 条，后续实现就可以直接按这版文档走。
