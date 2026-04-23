# PaperChatAgent 数据模型文档

## 1. 文档目标

本文档用于冻结 PaperChatAgent V1 的核心对象、关键关系和状态机，确保数据模型服务于“聊天主链路 + 模块化能力”。

本轮数据模型的第一原则是：

`会话是主对象，知识库 / 智能体 / 模型 / 工具 / 任务都是围绕会话协同工作的独立模块。`

## 2. 核心实体

### 2.1 User

表示登录用户。

建议字段：

- `id`
- `email`
- `password_hash`
- `display_name`
- `avatar_url`
- `status`
- `created_at`
- `updated_at`

### 2.2 UserSession

表示登录态与刷新令牌会话。

建议字段：

- `id`
- `user_id`
- `refresh_token_hash`
- `expires_at`
- `revoked_at`
- `created_at`
- `updated_at`

### 2.3 ChatSession

表示用户长期使用和切换的主对象。

建议字段：

- `id`
- `user_id`
- `title`
- `status`
- `memory_summary_text`
- `last_summarized_message_id`
- `last_message_at`
- `created_at`
- `updated_at`

约束：

- 聊天主链路以 `ChatSession` 为中心
- 长短期记忆都按 `ChatSession` 隔离

### 2.4 Message

表示会话中的单条消息。

建议字段：

- `id`
- `session_id`
- `role`
- `message_type`
- `content`
- `metadata_json`
- `created_at`

`message_type` 建议支持：

- `chat`
- `system_notice`
- `task_event`
- `tool_result`

### 2.5 CitationEvidence

表示消息所引用的来源依据。

建议字段：

- `id`
- `message_id`
- `knowledge_file_id`
- `citation_level`
- `label`
- `locator_json`
- `created_at`

### 2.6 KnowledgeBase

表示一个资料容器。

建议字段：

- `id`
- `user_id`
- `name`
- `description`
- `status`
- `created_at`
- `updated_at`

说明：

- 知识库是独立模块对象
- 一个知识库下可包含多个文件和切片

### 2.7 KnowledgeFile

表示知识库中的文件或外部资料。

建议字段：

- `id`
- `knowledge_base_id`
- `user_id`
- `source_type`
- `title`
- `source_url`
- `object_key`
- `parser_status`
- `index_status`
- `metadata_json`
- `created_at`
- `updated_at`

### 2.8 KnowledgeChunk

表示一个可检索切片。

建议字段：

- `id`
- `knowledge_file_id`
- `chunk_index`
- `content`
- `page_no`
- `section_title`
- `vector_collection`
- `vector_doc_id`
- `locator_json`
- `created_at`

### 2.9 SessionKnowledgeBinding

表示会话与知识库之间的绑定关系。

建议字段：

- `id`
- `session_id`
- `knowledge_base_id`
- `binding_type`
- `created_at`

说明：

- 允许一个会话绑定多个知识库
- 允许系统在聊天中自动建议绑定或创建知识库

### 2.10 ResearchTask

表示用户确认主题后触发的一次异步研究任务。

建议字段：

- `id`
- `user_id`
- `session_id`
- `title`
- `status`
- `current_node`
- `progress_percent`
- `detail`
- `payload_json`
- `checkpoint_json`
- `created_at`
- `updated_at`

说明：

- `ResearchTask` 来源于聊天，而不是来源于工作区概念

### 2.11 WorkflowRun

表示一次真实工作流执行。

建议字段：

- `id`
- `task_id`
- `workflow_id`
- `status`
- `current_node`
- `trace_json`
- `created_at`
- `updated_at`

### 2.12 WorkflowNodeRun

表示工作流中单个节点的运行状态。

建议字段：

- `id`
- `workflow_run_id`
- `node_id`
- `title`
- `status`
- `detail`
- `started_at`
- `completed_at`
- `metadata_json`

说明：

- 后台任务页主要消费该对象来展示智能体进度

### 2.13 TaskArtifact

表示任务产物或结果摘要。

建议字段：

- `id`
- `task_id`
- `artifact_type`
- `title`
- `summary`
- `content_markdown`
- `metadata_json`
- `created_at`
- `updated_at`

### 2.14 AgentWorkflow

表示一个已注册的智能体 / 工作流定义。

建议字段：

- `id`
- `name`
- `description`
- `status`
- `definition_json`
- `created_at`
- `updated_at`

### 2.15 McpServerConfig

表示一个 MCP 服务配置。

建议字段：

- `id`
- `user_id`
- `name`
- `transport_type`
- `endpoint`
- `auth_config_json`
- `metadata_json`
- `status`
- `created_at`
- `updated_at`

### 2.16 SkillConfig

表示一个 Skill 配置对象。

建议字段：

- `id`
- `user_id`
- `name`
- `source_type`
- `path_or_repo`
- `metadata_json`
- `status`
- `created_at`
- `updated_at`

### 2.17 ModelRouteConfig

表示逻辑模型槽位的路由配置。

建议字段：

- `id`
- `user_id`
- `route_key`
- `provider`
- `model_name`
- `base_url`
- `metadata_json`
- `status`
- `created_at`
- `updated_at`

`route_key` 至少包括：

- `conversation`
- `tool_call`
- `reasoning`
- `embedding`
- `rerank`

### 2.18 DashboardMetricSnapshot

表示用于数据看板的指标快照。

建议字段：

- `id`
- `metric_key`
- `metric_value`
- `dimension_json`
- `recorded_at`

## 3. 核心关系

### 3.1 User -> ChatSession

- 一个用户拥有多个会话
- 最近会话列表按 `ChatSession.updated_at` 展示

### 3.2 ChatSession -> Message

- 一个会话包含多条消息
- 消息按时间和顺序组织

### 3.3 ChatSession -> KnowledgeBase

- 会话与知识库之间通过绑定关系连接
- 绑定既可以由用户显式完成，也可以由系统建议后确认

### 3.4 KnowledgeBase -> KnowledgeFile -> KnowledgeChunk

- 一个知识库包含多个知识文件
- 一个知识文件产生多个可检索切片

### 3.5 ChatSession -> ResearchTask

- 研究任务由聊天触发
- 一个会话可以触发多个任务

### 3.6 ResearchTask -> WorkflowRun -> WorkflowNodeRun

- 一个任务对应一次或多次工作流运行
- 一个工作流运行下有多个节点运行记录

### 3.7 ResearchTask -> TaskArtifact

- 一个任务可以产出多个任务产物
- V1 至少需要支持结果摘要和 Markdown 报告类产物

### 3.8 User -> McpServerConfig / SkillConfig / ModelRouteConfig

- 这些配置都归属于用户
- 它们为聊天和任务执行提供能力支持

## 4. 状态机

### 4.1 ResearchTask

状态建议：

- `queued`
- `running`
- `paused`
- `completed`
- `failed`
- `canceled`

流转建议：

```text
queued -> running -> completed
queued -> running -> paused
paused -> running -> completed
paused -> running -> failed
queued -> canceled
running -> canceled
failed -> queued   # 创建新任务重试
```

### 4.2 WorkflowNodeRun

状态建议：

- `pending`
- `running`
- `retrying`
- `paused`
- `completed`
- `failed`
- `skipped`

### 4.3 KnowledgeFile

解析状态建议：

- `uploaded`
- `parsing`
- `parsed`
- `failed`

索引状态建议：

- `pending`
- `indexing`
- `indexed`
- `failed`

## 5. 数据归属边界

### 5.1 会话

- 会话归属于单一用户
- 不同会话之间默认不共享记忆

### 5.2 知识库

- 知识库归属于单一用户
- 同一知识库可服务多个会话

### 5.3 任务与工作流

- 任务归属于单一用户与单一会话
- 节点运行记录归属于单次工作流运行

### 5.4 配置模块

- MCP / Skills / 模型路由均按用户维度管理

## 6. 兼容与过渡说明

当前代码中仍存在以下旧对象或旧表语义：

- `InboxConversation`
- `ResearchWorkspace`
- `paperchat_workspaces`
- `chat_sessions.workspace_id`

新的数据模型口径如下：

- `ChatSession` 才是用户主对象
- `ResearchWorkspace` 不再作为产品层主对象
- 若当前实现仍使用 `workspace` 字段承载任务容器，应视为内部过渡结构

## 7. 统一类型名

后续文档优先使用以下类型名：

- `ChatSession`
- `Message`
- `KnowledgeBase`
- `KnowledgeFile`
- `KnowledgeChunk`
- `ResearchTask`
- `WorkflowRun`
- `WorkflowNodeRun`
- `TaskArtifact`
- `AgentWorkflow`
- `McpServerConfig`
- `SkillConfig`
- `ModelRouteConfig`

## 8. 非目标

本文档不覆盖：

- 字段级 migration 脚本
- 最终 SQL DDL
- 多租户模型
- 复杂版本化策略
