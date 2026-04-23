# PaperChatAgent API Contract V1

## 1. 文档目标

本文档用于冻结 PaperChatAgent V1 的 API 契约口径，使前后端围绕“聊天主链路 + 模块化能力”开发。

说明：

- 本文档定义的是目标契约
- 当前仓库并非所有接口都已完全实现
- 对于仍在使用的旧接口，会在兼容章节中特别说明

## 2. 通用约定

### 2.1 Base URL

- 本地开发前缀：`/api/v1`

### 2.2 成功响应

```json
{
  "code": "OK",
  "message": "success",
  "data": {},
  "request_id": "trace-id"
}
```

### 2.3 失败响应

```json
{
  "code": "AUTH_INVALID_CREDENTIALS",
  "message": "邮箱或密码错误",
  "details": {},
  "request_id": "trace-id"
}
```

### 2.4 通用原则

- 时间统一使用 `ISO 8601 UTC`
- ID 统一使用 UUID 字符串
- SSE 统一传递业务事件，而不是底层框架原始流对象
- 外部 API 不把 `ResearchWorkspace` 作为主对象暴露给前端

## 3. Auth

### 3.1 `POST /auth/register`

用途：

- 注册用户

核心返回：

- `user_id`
- `default_session_id`

### 3.2 `POST /auth/login`

用途：

- 登录并写入 Cookie

核心返回：

- `user`

### 3.3 `POST /auth/refresh`

用途：

- 刷新登录态

### 3.4 `POST /auth/logout`

用途：

- 清理 Cookie 并吊销当前登录会话

### 3.5 `GET /me`

用途：

- 恢复浏览器登录态

## 4. Chat

聊天是 V1 主链路，因此会话与消息接口是首要资源接口。

### 4.1 `GET /conversations`

用途：

- 返回最近会话列表

返回对象：

- `ChatSessionDTO[]`

`ChatSessionDTO` 至少包含：

- `id`
- `title`
- `status`
- `last_message_at`
- `updated_at`
- `last_message_preview`

### 4.2 `POST /conversations`

用途：

- 创建新会话

### 4.3 `GET /conversations/{id}/messages`

用途：

- 获取会话消息历史

返回对象：

- `MessageDTO[]`

`MessageDTO` 至少包含：

- `id`
- `role`
- `message_type`
- `content`
- `metadata`
- `citations`
- `created_at`

### 4.4 `POST /conversations/{id}/messages/stream`

用途：

- 发送消息并建立 SSE 响应流

请求体：

```json
{
  "content": "请帮我梳理这个研究方向",
  "client_message_id": "client-uuid",
  "attachment_ids": ["knowledge-file-id-1"],
  "metadata": {}
}
```

行为约束：

- 用户消息先落库
- 模型可在当前轮判断是否检索知识库
- 模型可在当前轮判断是否调用智能体、MCP、Skills
- 最终 assistant 消息在完成后落库

### 4.5 Chat SSE 事件

聊天 SSE 事件统一为：

- `message.started`
- `message.delta`
- `message.progress`
- `message.tool`
- `message.info`
- `message.completed`
- `message.failed`
- `ping`

`message.tool` 事件的 `tool` 字段允许表示：

- `knowledge_retrieval`
- `agent_workflow`
- `mcp_call`
- `skill_call`

## 5. Knowledge

知识库是独立模块，但主要服务于聊天阶段的按需检索。

### 5.1 `GET /knowledge/bases`

用途：

- 获取当前用户的知识库列表

### 5.2 `POST /knowledge/bases`

用途：

- 创建知识库

请求体至少包含：

- `name`
- `description`

### 5.3 `GET /knowledge/bases/{id}`

用途：

- 获取单个知识库详情

### 5.4 `POST /knowledge/files/upload`

用途：

- 上传知识文件

请求：

- `multipart/form-data`

返回对象：

- `KnowledgeFileDTO`

### 5.5 `POST /knowledge/import/arxiv`

用途：

- 从 arXiv 导入资料

### 5.6 `POST /knowledge/session-bindings`

用途：

- 把知识库绑定到某个会话

请求体至少包含：

- `session_id`
- `knowledge_base_id`
- `binding_type`

## 6. Agents

### 6.1 `GET /agents/workflows`

用途：

- 获取当前已注册工作流列表

### 6.2 `GET /agents/workflows/{id}`

用途：

- 获取单个工作流定义

### 6.3 `GET /agents/workflows/{id}/nodes`

用途：

- 获取工作流节点定义
- 若传入 `task_id`，则返回该任务对应的节点运行状态

返回对象：

- `WorkflowNodeRunDTO[]`

## 7. Tasks

后台任务页主要展示智能体 / 工作流执行进度，因此任务接口围绕任务与工作流运行展开。

### 7.1 `POST /tasks`

用途：

- 创建研究任务

请求体建议包含：

- `session_id`
- `topic`
- `keywords`
- `knowledge_base_ids`
- `source_config`

说明：

- 当前版本的任务会在 API 进程内异步执行
- `source_config` 可包含任务恢复策略，例如最大重试次数和备用模型覆盖配置

### 7.2 `GET /tasks`

用途：

- 获取任务列表

### 7.3 `GET /tasks/{id}`

用途：

- 获取任务详情，包括当前工作流与节点摘要

### 7.4 `GET /tasks/{id}/report`

用途：

- 获取任务产物或摘要报告

### 7.5 `GET /tasks/{id}/events`

用途：

- 订阅任务与工作流进度流

任务 SSE 事件统一为：

- `task.snapshot`
- `task.progress`
- `task.node.started`
- `task.node.retrying`
- `task.node.paused`
- `task.node.completed`
- `task.node.failed`
- `task.paused`
- `task.resumed`
- `task.completed`
- `task.failed`

其中：

- `task.snapshot` 返回任务当前全量快照
- `task.node.*` 用于后台任务页展示智能体节点进度

### 7.6 `POST /tasks/{id}/resume`

用途：

- 从失败节点恢复当前任务

请求体：

```json
{
  "resume_from_node": "analyse_agent_node",
  "model_slot_overrides": {
    "reasoning_model": "conversation_model"
  }
}
```

行为约束：

- 仅 `paused / failed` 状态允许恢复
- 恢复后从指定节点重新执行，并继续后续节点

## 8. MCP Services

### 8.1 `GET /mcp/servers`

用途：

- 获取 MCP 服务配置列表

### 8.2 `POST /mcp/servers`

用途：

- 新增 MCP 服务配置

### 8.3 `POST /mcp/servers/import-local`

用途：

- 导入本地 MCP 服务配置

## 9. Skills

### 9.1 `GET /skills`

用途：

- 获取 Skill 列表

### 9.2 `POST /skills`

用途：

- 新增 Skill 配置

### 9.3 `POST /skills/import-local`

用途：

- 导入本地 Skill

## 10. Models

### 10.1 `GET /models/routes`

用途：

- 获取模型槽位与路由配置

### 10.2 `PUT /models/routes`

用途：

- 更新模型路由配置

模型槽位至少包括：

- `conversation`
- `tool_call`
- `reasoning`
- `embedding`
- `rerank`

## 11. Dashboard

### 11.1 `GET /dashboard/overview`

用途：

- 获取系统观测摘要

返回对象建议包含：

- `model_call_count`
- `input_token_count`
- `output_token_count`
- `task_status_distribution`
- `recent_task_count`

## 12. 兼容接口说明

### 12.1 `GET /conversations/inbox`

该接口可继续保留，但定义为：

- 当前实现兼容接口
- 不再作为产品主对象入口

兼容原因：

- 当前前端与部分后端结构仍使用默认收件箱容器

### 12.2 Workspace 相关语义

新的 API 契约不再把 `workspace` 作为对前端的核心资源。

若当前实现中仍存在：

- `chat_sessions.workspace_id`
- `research_tasks.workspace_id`

则应视为内部兼容字段，不构成新产品主语义。

## 13. 契约冻结结论

PaperChatAgent V1 的 API 契约应满足：

- 会话是主资源对象
- 知识库、智能体、MCP、Skills、模型、后台任务、看板都是独立资源模块
- 聊天接口允许模型自主检索和工具调用
- 后台任务接口重点暴露工作流节点进度
