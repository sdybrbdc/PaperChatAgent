# PaperChatAgent 数据库设计文档

## 1. 文档目标

本文档在现有 [数据模型文档](./data-model.md) 之上，进一步把 V1 的业务对象落实到可建表粒度。  
目标是回答三个问题：

1. 现在到底需要创建哪些表
2. 会话记录表、消息表应该怎么设计
3. 完整 Paper-Agent 工作流接入后，中间结果和产物如何落库

本文档默认数据库为 `MySQL 8.0+`。

## 2. 设计原则

- 字符集统一采用 `utf8mb4`
- 主键统一使用应用侧生成的 `CHAR(36)` UUID
- 所有时间字段统一使用 UTC 时间戳
- 长文本优先使用 `LONGTEXT`
- 可扩展结构优先使用 `JSON`
- 与向量检索、对象存储相关的大对象不直接放 MySQL，MySQL 只保存索引、元数据和关系

## 3. 当前建议创建的表

下表是当前完整技术路线下建议直接创建的表。  
因为你已经决定吸收 `AgentChat + LangChain` 的聊天层，以及 `Paper-Agent + AutoGen + LangGraph` 的完整工作流，所以这里不是“最小 MVP 表集”，而是“当前路线可直接开工表集”。

| 分组 | 表名 | 说明 | 当前是否建议创建 |
|---|---|---|---|
| 认证 | `users` | 用户主表 | 是 |
| 认证 | `user_sessions` | 登录会话、刷新令牌、登出/吊销跟踪 | 是 |
| 收件箱 | `inbox_conversations` | 默认收件箱会话容器 | 是 |
| 工作区 | `research_workspaces` | 研究工作区主表 | 是 |
| 工作区 | `workspace_share_links` | 工作区只读分享链接 | 是 |
| 聊天 | `chat_sessions` | 会话容器，归属收件箱或工作区 | 是 |
| 聊天 | `messages` | 消息记录表，也是主要会话记录表 | 是 |
| 知识库 | `knowledge_bases` | 全局/私有知识库主表 | 是 |
| 知识库 | `workspace_knowledge_links` | 工作区与知识库绑定关系 | 是 |
| 知识库 | `knowledge_files` | PDF / arXiv 论文 / 外部文档资源 | 是 |
| 知识库 | `knowledge_chunks` | 文档切片与向量元数据 | 是 |
| 任务 | `research_tasks` | 研究任务主表 | 是 |
| 工作流 | `workflow_runs` | 一次完整工作流运行记录 | 是 |
| 工作流 | `workflow_node_runs` | 每个节点的执行记录 | 是 |
| 论文域 | `research_papers` | 搜索/导入得到的候选论文 | 是 |
| 论文域 | `extracted_papers` | 阅读节点提取出的结构化论文信息 | 是 |
| 分析域 | `analysis_clusters` | 聚类分析结果 | 是 |
| 分析域 | `analysis_cluster_papers` | 聚类与论文关联 | 是 |
| 分析域 | `analysis_reports` | 深度分析和全局分析结果 | 是 |
| 写作域 | `writing_outlines` | 写作主管节点生成的大纲 | 是 |
| 写作域 | `writing_sections` | 并行章节写作结果 | 是 |
| 报告域 | `report_artifacts` | Markdown / PDF / HTML 报告产物 | 是 |
| 产物域 | `topic_exploration_packages` | 主题探索包主表 | 是 |
| 引用域 | `citation_evidences` | 回答引用依据表 | 是 |

## 4. 会话与消息实现细节

你特别提到“从会话记录表开始”，所以这里先把聊天相关表单独讲细。

### 4.1 `inbox_conversations`

用途：

- 每个用户默认有一个收件箱会话容器
- 用于承载“研究方向还没明确前”的默认聊天入口

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | `CHAR(36)` | PK | 收件箱会话 ID |
| `user_id` | `CHAR(36)` | UK, FK | 一个用户默认一条 |
| `title` | `VARCHAR(255)` | NOT NULL | 默认标题 |
| `status` | `VARCHAR(32)` | NOT NULL | `active / archived` |
| `summary` | `TEXT` | NULL | 历史总结 |
| `last_message_at` | `DATETIME` | NULL | 最近消息时间 |
| `created_at` | `DATETIME` | NOT NULL | 创建时间 |
| `updated_at` | `DATETIME` | NOT NULL | 更新时间 |

建议索引：

- `uk_inbox_conversations_user_id (user_id)`
- `idx_inbox_conversations_last_message_at (last_message_at)`

### 4.2 `chat_sessions`

用途：

- 真正挂消息的会话容器
- 会话既可能属于收件箱，也可能属于某个工作区

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | `CHAR(36)` | PK | 会话 ID |
| `user_id` | `CHAR(36)` | FK | 所属用户 |
| `workspace_id` | `CHAR(36)` | NULL, FK | 工作区会话时有值 |
| `inbox_conversation_id` | `CHAR(36)` | NULL, FK | 收件箱会话时有值 |
| `session_scope` | `VARCHAR(32)` | NOT NULL | `inbox / workspace` |
| `title` | `VARCHAR(255)` | NOT NULL | 会话标题 |
| `status` | `VARCHAR(32)` | NOT NULL | `active / archived / deleted` |
| `summary` | `TEXT` | NULL | 历史摘要 |
| `last_message_at` | `DATETIME` | NULL | 最近消息时间 |
| `created_at` | `DATETIME` | NOT NULL | 创建时间 |
| `updated_at` | `DATETIME` | NOT NULL | 更新时间 |

约束说明：

- `session_scope = inbox` 时必须绑定 `inbox_conversation_id`
- `session_scope = workspace` 时必须绑定 `workspace_id`
- 业务上不允许两个归属字段同时为空

建议索引：

- `idx_chat_sessions_user_id (user_id)`
- `idx_chat_sessions_workspace_id (workspace_id)`
- `idx_chat_sessions_inbox_conversation_id (inbox_conversation_id)`
- `idx_chat_sessions_last_message_at (last_message_at)`

### 4.3 `messages`

这是当前项目最核心的“会话记录表”。

用途：

- 记录用户消息、AI 回复、系统提示、任务建议消息
- 保存引用依据关联、结构化事件载荷、消息顺序

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | `CHAR(36)` | PK | 消息 ID |
| `session_id` | `CHAR(36)` | FK | 所属会话 |
| `user_id` | `CHAR(36)` | NULL, FK | 用户消息时可回溯发起者 |
| `role` | `VARCHAR(16)` | NOT NULL | `user / assistant / system` |
| `message_type` | `VARCHAR(32)` | NOT NULL | `chat / task_suggestion / task_event / report / system_notice` |
| `sequence_no` | `INT` | NOT NULL | 会话内顺序号 |
| `content` | `LONGTEXT` | NOT NULL | 主文本内容 |
| `content_json` | `JSON` | NULL | 结构化消息载荷 |
| `citation_payload` | `JSON` | NULL | 内联引用数据快照 |
| `metadata_json` | `JSON` | NULL | 扩展元数据 |
| `input_tokens` | `INT` | NOT NULL | 输入 token 数 |
| `output_tokens` | `INT` | NOT NULL | 输出 token 数 |
| `created_at` | `DATETIME` | NOT NULL | 创建时间 |

建议索引：

- `uk_messages_session_seq (session_id, sequence_no)`
- `idx_messages_session_created (session_id, created_at)`
- `idx_messages_role (role)`
- `idx_messages_message_type (message_type)`

实现建议：

- 前端按 `sequence_no` 排序展示，而不是依赖 `created_at`
- 一旦消息落库，不直接覆盖原文，修改走补充系统消息或版本化策略
- `citation_payload` 保存的是展示层快照，结构化引用主数据仍落在 `citation_evidences`

## 5. 其余核心表说明

### 5.1 用户与认证

#### `users`

用户主表，采用邮箱密码登录。

关键点：

- `email` 必须唯一
- `password_hash` 不保存明文密码
- `status` 建议支持 `active / disabled`

#### `user_sessions`

用于支撑 JWT + Cookie 登录态的会话追踪、刷新令牌、登出吊销。

建议保存：

- `refresh_token_hash`
- `expires_at`
- `last_seen_at`
- `revoked_at`
- `user_agent`
- `ip_address`

### 5.2 工作区

#### `research_workspaces`

研究主题的长期容器，关联默认收件箱转化来源。

关键点：

- `origin_inbox_conversation_id` 记录收件箱来源
- `status` 建议支持 `active / archived`
- 工作区名称对同一用户建议唯一

#### `workspace_share_links`

工作区只读分享表。

关键点：

- `share_token` 唯一
- 可设置 `expires_at`
- 可记录 `is_enabled`

### 5.3 知识库

#### `knowledge_bases`

知识库容器，分为：

- `global`
- `workspace_private`

关键点：

- `scope = global` 时 `workspace_id` 必须为空
- `scope = workspace_private` 时 `workspace_id` 必须有值

#### `workspace_knowledge_links`

记录工作区挂接了哪些知识库。

用途：

- 让全局知识库可复用到多个工作区
- 保留工作区与知识库的关系轨迹

#### `knowledge_files`

文件/论文主表，承载上传 PDF 与 arXiv 资源。

建议状态拆分：

- `parser_status`
  - `uploaded / parsing / parsed / failed`
- `index_status`
  - `pending / indexing / indexed / failed`

#### `knowledge_chunks`

切片与向量元数据表。

用途：

- 记录 chunk 来源和定位信息
- 让引用依据能回溯到 chunk

建议字段包括：

- `chunk_index`
- `page_no`
- `section_title`
- `chunk_hash`
- `vector_collection`
- `vector_doc_id`
- `locator_json`

### 5.4 任务与工作流

#### `research_tasks`

研究任务主表，对应前端“后台任务”列表。

关键点：

- `status`: `queued / running / completed / failed / canceled`
- `current_node`: 当前执行节点
- `payload_json`: 原始任务配置快照

#### `workflow_runs`

一次完整工作流运行记录。

关键点：

- `workflow_name` 记录当前运行的是哪套图
- `node_statuses_json` 保存五大节点状态快照
- `trace_json` 预留调试与链路追踪

#### `workflow_node_runs`

每个节点一条运行记录。

用于：

- 后台任务页展示阶段进度
- 精确定位失败节点
- 为后续可视化任务图做数据支持

### 5.5 完整研究工作流中间表

#### `research_papers`

记录任务级候选论文。

字段重点：

- `paper_identifier`：例如 arXiv ID / DOI
- `selection_status`
- `pdf_url`
- `metadata_json`

#### `extracted_papers`

记录阅读节点抽取的结构化论文信息。

字段重点：

- `core_problem`
- `key_methodology_name`
- `key_methodology_principle`
- `key_methodology_novelty`
- `datasets_json`
- `evaluation_metrics_json`
- `main_results`
- `limitations`
- `contributions_json`

#### `analysis_clusters`

聚类结果表。

#### `analysis_cluster_papers`

聚类与论文的多对多关系表。

#### `analysis_reports`

存储：

- 单个聚类分析结果
- 全局分析结果

### 5.6 写作与报告

#### `writing_outlines`

写作主管节点生成的大纲。

#### `writing_sections`

并行章节写作结果。

字段重点：

- `section_key`
- `section_order`
- `status`
- `review_status`
- `sources_json`

#### `report_artifacts`

报告产物表。

支持：

- Markdown
- HTML
- PDF
- JSON 摘要

### 5.7 最终产物与引用

#### `topic_exploration_packages`

主题探索包主表，连接工作区、任务、报告和问答上下文。

#### `citation_evidences`

引用依据主表。

建议支持三种引用层级：

- `paper`
- `section`
- `paragraph`

建议可选引用来源：

- `knowledge_file_id`
- `knowledge_chunk_id`
- `research_paper_id`

## 6. 当前推荐建表顺序

建议按以下顺序建表，避免外键依赖冲突：

1. `users`
2. `user_sessions`
3. `inbox_conversations`
4. `research_workspaces`
5. `workspace_share_links`
6. `chat_sessions`
7. `messages`
8. `knowledge_bases`
9. `workspace_knowledge_links`
10. `knowledge_files`
11. `knowledge_chunks`
12. `research_tasks`
13. `workflow_runs`
14. `workflow_node_runs`
15. `research_papers`
16. `extracted_papers`
17. `analysis_clusters`
18. `analysis_cluster_papers`
19. `analysis_reports`
20. `writing_outlines`
21. `writing_sections`
22. `report_artifacts`
23. `topic_exploration_packages`
24. `citation_evidences`

## 7. SQL 脚本

完整 MySQL 初始化脚本见：

- [sql/mysql_init.sql](../sql/mysql_init.sql)

该脚本包含：

- 数据库创建
- 24 张业务表
- 主键、唯一键、外键
- 核心索引

## 8. 从注册到工作流完成的落表流程

这一节按“用户真实使用顺序”说明每一步会读写哪些表。

| 阶段 | 入口动作 | 主要写入表 | 主要读取表 | 说明 |
|---|---|---|---|---|
| 1 | 用户注册 | `users`、`inbox_conversations`、`chat_sessions` | 无 | 注册后立即具备默认聊天入口 |
| 2 | 用户登录 | `user_sessions` | `users` | 登录成功后写 Cookie 会话与 refresh 记录 |
| 3 | 打开默认聊天页 | 无 | `inbox_conversations`、`chat_sessions`、`messages` | 获取默认收件箱会话与消息历史 |
| 4 | 发送聊天消息 | `messages` | `chat_sessions`、`knowledge_bases`、`knowledge_chunks` | 先写用户消息，再生成 AI 回复消息 |
| 5 | 上传 PDF / 导入 arXiv | `knowledge_bases`（按需）、`knowledge_files` | `users`、`knowledge_bases` | 首次上传可自动创建全局知识库 |
| 6 | AI 生成任务建议 | `messages` | `messages`、`knowledge_files` | assistant 消息类型为 `task_suggestion` |
| 7 | 用户确认研究任务 | `research_workspaces`、`research_tasks`、`workflow_runs`、`workflow_node_runs`、`workspace_knowledge_links` | `chat_sessions`、`knowledge_files` | 若未指定工作区则自动创建 |
| 8 | 搜索节点执行 | `research_papers`、`workflow_node_runs` | `research_tasks` | 保存候选论文列表 |
| 9 | 阅读节点执行 | `extracted_papers`、`knowledge_chunks`、`workflow_node_runs` | `research_papers`、`knowledge_files` | 保存结构化抽取与切片 |
| 10 | 分析节点执行 | `analysis_clusters`、`analysis_cluster_papers`、`analysis_reports`、`workflow_node_runs` | `extracted_papers` | 保存聚类与全局分析 |
| 11 | 写作节点执行 | `writing_outlines`、`writing_sections`、`workflow_node_runs` | `analysis_reports`、`knowledge_chunks` | 生成大纲与章节 |
| 12 | 报告节点执行 | `report_artifacts`、`topic_exploration_packages`、`workflow_node_runs` | `writing_sections` | 形成最终报告与主题探索包 |
| 13 | 后续问答 | `messages`、`citation_evidences` | `topic_exploration_packages`、`report_artifacts`、`knowledge_chunks` | 回答必须附引用依据 |

## 9. 当前默认实现细节

如果没有新的产品决策，数据库层建议直接按以下默认值落地：

1. `users` 创建成功后同步创建：
   - `inbox_conversations`
   - 一个默认 `chat_sessions`

2. `knowledge_bases` 采用延迟创建：
   - 用户第一次上传资料时才创建账号级全局知识库

3. `research_tasks` 创建时一定初始化：
   - 一条 `workflow_runs`
   - 五条 `workflow_node_runs`

4. `topic_exploration_packages` 与 `report_artifacts` 都保留：
   - 前者服务后续问答
   - 后者服务报告下载与展示
