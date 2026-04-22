# PaperChatAgent 数据模型文档

## 1. 文档目标

本文档用于冻结 V1 的核心业务对象、关键关系和状态机，避免实现阶段因对象命名或归属边界不清导致重复返工。

## 2. 核心实体

### 2.1 User

表示登录用户。

建议字段：

- `id`
- `email`
- `password_hash`
- `display_name`
- `created_at`
- `updated_at`

### 2.2 InboxConversation

表示用户的默认容器，用于承接初始会话，不直接作为聊天前端主对象。

建议字段：

- `id`
- `user_id`
- `title`
- `status`
- `created_at`
- `updated_at`

说明：

- 每个用户默认至少有一个 `InboxConversation`
- 新创建的聊天会话默认可挂在该容器下

### 2.3 ResearchWorkspace

表示围绕一个研究主题建立的长期空间。

建议字段：

- `id`
- `user_id`
- `name`
- `description`
- `origin_inbox_conversation_id`
- `status`
- `share_token`
- `created_at`
- `updated_at`

### 2.4 ChatSession

表示聊天主对象，是用户实际感知和切换的“最近会话”。

建议字段：

- `id`
- `user_id`
- `workspace_id`（可空）
- `inbox_conversation_id`（可空）
- `title`
- `memory_summary_text`
- `last_summarized_message_id`
- `created_at`
- `updated_at`

约束：

- `workspace_id` 与 `inbox_conversation_id` 至少有一个存在
- 当前聊天主流程仅依赖 `ChatSession`
- 长短期记忆都按 `ChatSession` 隔离

### 2.5 Message

表示单条消息。

建议字段：

- `id`
- `session_id`
- `role`
- `content`
- `message_type`
- `citation_payload`
- `created_at`

说明：

- `role` 可取 `user / assistant / system`
- `message_type` 可区分普通消息、任务建议、系统提示

### 2.6 KnowledgeBase

表示知识库容器。

建议字段：

- `id`
- `user_id`
- `workspace_id`（可空）
- `name`
- `scope`
- `created_at`
- `updated_at`

`scope` 取值建议：

- `global`
- `workspace_private`

### 2.7 KnowledgeFile

表示知识库中的文件或论文资源。

建议字段：

- `id`
- `knowledge_base_id`
- `workspace_id`（可空）
- `source_type`
- `title`
- `source_url`
- `object_key`
- `status`
- `metadata_json`
- `created_at`
- `updated_at`

`source_type` 建议：

- `upload_pdf`
- `arxiv`

### 2.8 ResearchTask

表示一次异步研究流程。

建议字段：

- `id`
- `user_id`
- `workspace_id`
- `title`
- `status`
- `task_type`
- `payload_json`
- `result_summary`
- `current_node`
- `created_at`
- `started_at`
- `finished_at`

### 2.9 TopicExplorationPackage

表示研究任务完成后沉淀出的主题语料上下文。

建议字段：

- `id`
- `workspace_id`
- `task_id`
- `title`
- `summary`
- `package_json`
- `report_markdown`（可空）
- `created_at`
- `updated_at`

### 2.10 CitationEvidence

表示回答所引用的来源依据。

建议字段：

- `id`
- `message_id`
- `knowledge_file_id`
- `citation_level`
- `label`
- `locator_json`
- `created_at`

`citation_level` 建议：

- `paper`
- `section`
- `paragraph`

### 2.11 WorkflowRun

表示研究工作流某一次实际运行记录。

建议字段：

- `id`
- `task_id`
- `workflow_name`
- `current_node`
- `status`
- `node_statuses_json`
- `trace_json`
- `created_at`
- `updated_at`

## 3. 核心关系

## 3.1 InboxConversation -> ChatSession

`InboxConversation` 作为系统默认容器存在，但前端主体验围绕 `ChatSession` 展开。

实现约束：

- 用户进入系统后至少拥有一个默认 `ChatSession`
- 用户可继续创建多个新的 `ChatSession`
- 最近会话列表按 `ChatSession.updated_at` 展示

## 3.2 全局知识库 + 工作区私有知识库

知识库模型采用双层结构：

- `全局知识库`
  - 归属于用户
  - 不归属于具体工作区
  - 可跨工作区复用

- `工作区私有知识库`
  - 归属于单个工作区
  - 只服务当前研究主题
  - 不被其他工作区直接复用

## 3.3 ResearchTask -> TopicExplorationPackage

- 一个 `ResearchTask` 在成功完成后，可以生成一个或多个 `TopicExplorationPackage`
- V1 默认按“每个任务产出一个主探索包”组织

## 3.4 ChatSession -> 会话级记忆

- 短期记忆来自当前会话最近消息窗口
- 长期记忆来自 `ChatSession.memory_summary_text`
- 不同会话之间不共享记忆

## 3.5 分享链接

- 分享链接与 `ResearchWorkspace` 关联
- 分享为只读，不产生新的业务实体副本
- 分享访问不允许修改源对象

## 4. 状态机

### 4.1 ResearchTask

状态：

- `queued`
- `running`
- `completed`
- `failed`
- `canceled`

流转建议：

```text
queued -> running -> completed
queued -> running -> failed
queued -> canceled
running -> canceled
failed -> queued   # retry
```

### 4.1.1 WorkflowNodeStatus

`WorkflowNodeStatus` 建议统一取值：

- `pending`
- `running`
- `completed`
- `failed`
- `skipped`

默认节点集合：

- `search_agent_node`
- `reading_agent_node`
- `analyse_agent_node`
- `writing_agent_node`
- `report_agent_node`

### 4.2 KnowledgeFile

状态：

- `uploaded`
- `parsing`
- `indexed`
- `attached`
- `failed`

流转建议：

```text
uploaded -> parsing -> indexed -> attached
uploaded -> parsing -> failed
indexed -> attached
failed -> parsing   # retry
```

### 4.3 WorkflowRun

状态：

- `queued`
- `running`
- `completed`
- `failed`

## 5. 数据归属边界

### 5.1 用户与工作区

- 所有工作区归属于单一用户
- V1 不支持多人共用同一工作区编辑

### 5.2 全局知识库

- 归属用户
- 不归属单工作区
- 可被多个工作区引用

### 5.3 工作区私有知识库

- 归属用户与单一工作区
- 不能被其他工作区直接共享

### 5.4 分享链接

- 只读访问工作区结果
- 不复制、不迁移、不改写源实体

## 6. 表/模型草案层级

### 6.1 用户与认证

- `users`
- `auth_sessions`（如需要）
- `refresh_tokens`（如需要）

### 6.2 会话与消息

- `inbox_conversations`
- `chat_sessions`
- `messages`
- `session_memories`（若不直接复用 `chat_sessions` 字段）

### 6.3 工作区与分享

- `research_workspaces`
- `workspace_share_links`

### 6.4 知识库与文件

- `knowledge_bases`
- `knowledge_files`
- `workspace_knowledge_links`

### 6.5 任务与工作流

- `research_tasks`
- `workflow_runs`
- `workflow_node_events`（可选）

### 6.6 主题探索包与引用依据

- `topic_exploration_packages`
- `citation_evidences`
- `report_artifacts`（可选）

## 7. 统一类型名

后续文档和代码中统一使用以下类型名：

- `InboxConversation`
- `ResearchWorkspace`
- `ResearchTask`
- `TopicExplorationPackage`
- `CitationEvidence`
- `KnowledgeFile`
- `WorkflowNodeStatus`

## 8. 与完整工作流的关系

当前数据模型不再只服务“聊天 + 轻量任务”，而是明确支持完整的 `AutoGen + LangGraph` 研究工作流：

- 搜索节点负责生成结构化检索输入与 HITL 审查状态
- 阅读节点负责结构化论文抽取结果
- 分析节点负责聚类与全局分析结果
- 写作节点负责章节与写作过程状态
- 报告节点负责最终 Markdown 报告工件

如果某阶段的 UI 尚未完全开放，数据模型仍然为这些工作流阶段预留持久化空间。

## 8. 非目标

本文档不覆盖：

- 字段级 migration 脚本
- 最终 SQL DDL
- 复杂版本化策略
- 多租户设计
