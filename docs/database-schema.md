# PaperChatAgent 数据库设计文档

## 1. 文档目标

本文档在 [数据模型文档](./data-model.md) 基础上，把 PaperChatAgent V1 的对象关系落到数据库设计层。

本轮数据库设计围绕以下结论展开：

- 用户主对象是 `ChatSession`
- 知识库、智能体、模型、MCP、Skills、后台任务、看板都是独立模块
- 后台任务页主要展示工作流运行与节点进度
- 旧的 `workspace` 相关结构只保留为当前实现的过渡兼容

## 2. 设计原则

- 字符集统一使用 `utf8mb4`
- 主键统一采用 UUID 字符串
- 所有时间字段统一使用 UTC
- 大文本使用 `TEXT` 或 `LONGTEXT`
- 可扩展结构优先使用 `JSON`
- 文件与向量不直接存 MySQL，MySQL 只保存索引、元数据和关系

## 3. 目标表集合

| 分组 | 表名 | 说明 |
|---|---|---|
| 认证 | `users` | 用户主表 |
| 认证 | `user_sessions` | 登录态与刷新令牌 |
| 聊天 | `chat_sessions` | 会话主表 |
| 聊天 | `messages` | 消息表 |
| 聊天 | `citation_evidences` | 引用依据 |
| 知识库 | `knowledge_bases` | 知识库主表 |
| 知识库 | `knowledge_files` | 知识文件 |
| 知识库 | `knowledge_chunks` | 文本切片与向量定位 |
| 知识库 | `session_knowledge_bindings` | 会话与知识库绑定关系 |
| 任务 | `research_tasks` | 研究任务 |
| 工作流 | `workflow_runs` | 工作流运行主表 |
| 工作流 | `workflow_node_runs` | 节点运行状态 |
| 产物 | `task_artifacts` | 任务产物与摘要 |
| 智能体 | `agent_workflows` | 智能体 / 工作流定义 |
| MCP | `mcp_server_configs` | MCP 配置 |
| Skills | `skill_configs` | Skill 配置 |
| 模型 | `model_route_configs` | 模型路由配置 |
| 看板 | `model_invocation_logs` | 模型调用日志 |
| 看板 | `dashboard_metric_snapshots` | 指标快照 |

## 4. 核心表设计

### 4.1 `chat_sessions`

用途：

- 用户实际感知和切换的主对象

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `CHAR(36)` | PK |
| `user_id` | `CHAR(36)` | FK |
| `title` | `VARCHAR(255)` | 会话标题 |
| `status` | `VARCHAR(32)` | `active / archived / deleted` |
| `memory_summary_text` | `TEXT` | 会话长期摘要 |
| `last_summarized_message_id` | `CHAR(36)` | 最近摘要截点 |
| `last_message_at` | `DATETIME` | 最近消息时间 |
| `created_at` | `DATETIME` | 创建时间 |
| `updated_at` | `DATETIME` | 更新时间 |

建议索引：

- `idx_chat_sessions_user_id`
- `idx_chat_sessions_updated_at`

### 4.2 `messages`

用途：

- 存储聊天消息、系统消息、工具结果或任务事件消息

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `CHAR(36)` | PK |
| `session_id` | `CHAR(36)` | FK |
| `user_id` | `CHAR(36)` | 可空，用户消息发起者 |
| `role` | `VARCHAR(16)` | `user / assistant / system` |
| `message_type` | `VARCHAR(32)` | `chat / tool_result / task_event / system_notice` |
| `content` | `LONGTEXT` | 主内容 |
| `metadata_json` | `JSON` | 扩展元数据 |
| `created_at` | `DATETIME` | 创建时间 |

建议索引：

- `idx_messages_session_created`
- `idx_messages_type`

### 4.3 `citation_evidences`

用途：

- 保存消息引用来源

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `CHAR(36)` | PK |
| `message_id` | `CHAR(36)` | FK |
| `knowledge_file_id` | `CHAR(36)` | FK |
| `citation_level` | `VARCHAR(32)` | `paper / section / paragraph` |
| `label` | `VARCHAR(255)` | 展示标签 |
| `locator_json` | `JSON` | 定位信息 |
| `created_at` | `DATETIME` | 创建时间 |

### 4.4 `knowledge_bases`

用途：

- 表示一个资料容器

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `CHAR(36)` | PK |
| `user_id` | `CHAR(36)` | FK |
| `name` | `VARCHAR(255)` | 名称 |
| `description` | `TEXT` | 描述 |
| `status` | `VARCHAR(32)` | `active / archived` |
| `created_at` | `DATETIME` | 创建时间 |
| `updated_at` | `DATETIME` | 更新时间 |

### 4.5 `knowledge_files`

用途：

- 保存单个知识文件元数据与状态

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `CHAR(36)` | PK |
| `knowledge_base_id` | `CHAR(36)` | FK |
| `user_id` | `CHAR(36)` | FK |
| `source_type` | `VARCHAR(32)` | `upload_pdf / arxiv / web_import` |
| `title` | `VARCHAR(512)` | 标题 |
| `source_url` | `VARCHAR(1024)` | 来源地址 |
| `object_key` | `VARCHAR(512)` | MinIO 键 |
| `parser_status` | `VARCHAR(32)` | 解析状态 |
| `index_status` | `VARCHAR(32)` | 索引状态 |
| `metadata_json` | `JSON` | 扩展元数据 |
| `created_at` | `DATETIME` | 创建时间 |
| `updated_at` | `DATETIME` | 更新时间 |

### 4.6 `knowledge_chunks`

用途：

- 保存切片级检索定位信息

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `CHAR(36)` | PK |
| `knowledge_file_id` | `CHAR(36)` | FK |
| `chunk_index` | `INT` | 切片序号 |
| `content` | `LONGTEXT` | 切片内容 |
| `page_no` | `INT` | 页码 |
| `section_title` | `VARCHAR(255)` | 节标题 |
| `vector_collection` | `VARCHAR(255)` | 向量集合名 |
| `vector_doc_id` | `VARCHAR(255)` | 向量文档 id |
| `locator_json` | `JSON` | 定位信息 |
| `created_at` | `DATETIME` | 创建时间 |

### 4.7 `session_knowledge_bindings`

用途：

- 保存会话与知识库之间的绑定关系

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `CHAR(36)` | PK |
| `session_id` | `CHAR(36)` | FK |
| `knowledge_base_id` | `CHAR(36)` | FK |
| `binding_type` | `VARCHAR(32)` | `manual / suggested / auto_created` |
| `created_at` | `DATETIME` | 创建时间 |

### 4.8 `research_tasks`

用途：

- 保存主题确认后触发的异步研究任务

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `CHAR(36)` | PK |
| `user_id` | `CHAR(36)` | FK |
| `session_id` | `CHAR(36)` | FK |
| `title` | `VARCHAR(255)` | 任务标题 |
| `status` | `VARCHAR(32)` | 任务状态 |
| `current_node` | `VARCHAR(64)` | 当前节点 |
| `progress_percent` | `FLOAT` | 进度百分比 |
| `detail` | `TEXT` | 运行说明 |
| `payload_json` | `JSON` | 任务输入 |
| `checkpoint_json` | `JSON` | 节点 checkpoint、失败上下文与恢复策略 |
| `created_at` | `DATETIME` | 创建时间 |
| `updated_at` | `DATETIME` | 更新时间 |

### 4.9 `workflow_runs`

用途：

- 保存一次工作流真实运行

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `CHAR(36)` | PK |
| `task_id` | `CHAR(36)` | FK |
| `workflow_id` | `CHAR(36)` | FK |
| `status` | `VARCHAR(32)` | 运行状态 |
| `current_node` | `VARCHAR(64)` | 当前节点 |
| `trace_json` | `JSON` | 跟踪信息 |
| `created_at` | `DATETIME` | 创建时间 |
| `updated_at` | `DATETIME` | 更新时间 |

### 4.10 `workflow_node_runs`

用途：

- 后台任务页的核心数据表

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `CHAR(36)` | PK |
| `workflow_run_id` | `CHAR(36)` | FK |
| `node_id` | `VARCHAR(64)` | 节点标识 |
| `title` | `VARCHAR(255)` | 节点标题 |
| `status` | `VARCHAR(32)` | 节点状态 |
| `detail` | `TEXT` | 当前说明 |
| `metadata_json` | `JSON` | 节点扩展数据 |
| `started_at` | `DATETIME` | 开始时间 |
| `completed_at` | `DATETIME` | 完成时间 |

说明：

- 当前实现中的节点运行数据暂由任务 `checkpoint_json` 持久化承载
- 后续若需要拆成正式表，可平滑迁移到 `workflow_node_runs`

### 4.11 `task_artifacts`

用途：

- 保存任务结果摘要、Markdown 报告等产物

建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `CHAR(36)` | PK |
| `task_id` | `CHAR(36)` | FK |
| `artifact_type` | `VARCHAR(32)` | `summary / markdown / report` |
| `title` | `VARCHAR(255)` | 标题 |
| `summary` | `TEXT` | 摘要 |
| `content_markdown` | `LONGTEXT` | Markdown 内容 |
| `metadata_json` | `JSON` | 扩展元数据 |
| `created_at` | `DATETIME` | 创建时间 |
| `updated_at` | `DATETIME` | 更新时间 |

### 4.12 配置与观测表

建议补充以下表：

- `agent_workflows`
- `mcp_server_configs`
- `skill_configs`
- `model_route_configs`
- `model_invocation_logs`
- `dashboard_metric_snapshots`

这些表分别负责：

- 注册工作流定义
- 保存 MCP / Skills 配置
- 保存模型槽位路由
- 记录模型调用
- 提供看板指标来源

## 5. 当前实现兼容说明

当前仓库已存在或已使用的结构包括：

- `paperchat_inbox_conversations`
- `paperchat_workspaces`
- `paperchat_chat_sessions.workspace_id`
- `paperchat_research_tasks.workspace_id`

这些结构在新文档中的解释如下：

- `InboxConversation` 仅作为当前兼容容器
- `ResearchWorkspace` 不再是产品主对象
- 若 `workspace_id` 仍存在，应视作内部任务容器或过渡字段
- 新的 API 与产品语义不应继续放大 `workspace` 概念

## 6. 迁移方向

数据库演进方向建议为：

1. 保留现有兼容字段，避免一次性破坏当前联调
2. 新增 `session_id` 驱动的任务与绑定关系
3. 新增知识库、配置模块、观测模块相关表
4. 逐步把旧的 `workspace` 语义降级为内部兼容实现

## 7. 非目标

本文档不包含：

- 完整 SQL DDL
- 实际 migration 文件
- 数据归档策略
- 分库分表方案
