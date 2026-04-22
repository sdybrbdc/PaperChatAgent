# PaperChatAgent API Contract v1

## 1. 文档目标

本文档用于冻结 PaperChatAgent V1 的首批后端 API 契约，重点覆盖：

- 通用响应格式
- 认证与登录态恢复
- 默认聊天页与消息流
- 后台任务进度流
- 分页与错误码约定

默认原则：

- 浏览器主链路采用 `Cookie 优先`
- 聊天流由 `LangChain / LangGraph` 负责产生，`FastAPI` 负责通过 `SSE` 传输
- 聊天接口对前端暴露业务事件，而不是直接暴露 LangGraph `StreamPart`

## 2. 通用约定

### 2.1 Base URL

- 本地开发前缀：`/api/v1`

### 2.2 成功响应

成功响应统一结构：

```json
{
  "code": "OK",
  "message": "success",
  "data": {},
  "request_id": "trace-id"
}
```

说明：

- `code`：稳定业务码，成功固定为 `OK`
- `message`：人类可读描述
- `data`：业务数据载荷
- `request_id`：由后端中间件生成并回传

### 2.3 失败响应

失败响应统一结构：

```json
{
  "code": "AUTH_INVALID_CREDENTIALS",
  "message": "邮箱或密码错误",
  "details": {},
  "request_id": "trace-id"
}
```

说明：

- HTTP 状态码表达传输层结果
- `code` 表达稳定业务错误语义
- `details` 仅在需要补充字段级信息时返回

### 2.4 时间、ID 与枚举

- 时间：统一使用 `ISO 8601 UTC`
- ID：统一使用 UUID 字符串
- 枚举：统一采用小写下划线，如 `task_suggestion`

## 3. Auth

### 3.1 认证策略

- 浏览器主链路采用 `HttpOnly Cookie`
- 后端同时兼容 `Authorization: Bearer <token>`
- 前端正式链路默认不把 access token 持久化到 `localStorage`
- 前端普通请求统一开启 `withCredentials: true`
- 前端 SSE 请求统一开启 `credentials: "include"`

默认参数：

- access token：1 天
- refresh token：30 天
- `SameSite=Lax`
- 生产环境 `Secure=true`

### 3.2 `POST /auth/register`

请求体：

```json
{
  "email": "user@example.com",
  "password": "plain-password",
  "display_name": "alice"
}
```

成功响应：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "user_id": "uuid",
    "inbox_conversation_id": "uuid",
    "default_session_id": "uuid"
  },
  "request_id": "trace-id"
}
```

后端行为：

1. 校验邮箱唯一性
2. hash 密码
3. 创建 `users`
4. 创建 `inbox_conversations`
5. 创建一个默认 `chat_sessions(session_scope=inbox)`

### 3.3 `POST /auth/login`

请求体：

```json
{
  "email": "user@example.com",
  "password": "plain-password"
}
```

成功响应：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "display_name": "alice",
      "avatar_url": ""
    }
  },
  "request_id": "trace-id"
}
```

响应副作用：

- 写入 access / refresh `HttpOnly Cookie`
- 创建一条 `user_sessions`

### 3.4 `POST /auth/refresh`

用途：

- 使用 refresh cookie 续期 access / refresh cookies

成功响应：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "refreshed": true
  },
  "request_id": "trace-id"
}
```

### 3.5 `POST /auth/logout`

用途：

- 清理浏览器 cookies
- 吊销当前 `user_sessions`

成功响应：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "logged_out": true
  },
  "request_id": "trace-id"
}
```

### 3.6 `GET /me`

用途：

- 前端启动时恢复登录态
- 路由守卫判断当前浏览器会话是否仍有效

成功响应：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "alice",
    "avatar_url": ""
  },
  "request_id": "trace-id"
}
```

## 4. Chat

### 4.1 `GET /conversations`

用途：

- 返回当前用户最近会话列表

成功响应：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "items": [
      {
        "id": "uuid",
        "title": "新聊天",
        "scope": "inbox",
        "status": "active",
        "last_message_at": "2026-04-22T10:00:00Z",
        "updated_at": "2026-04-22T10:00:00Z",
        "last_message_preview": "最近一条消息摘要"
      }
    ]
  },
  "request_id": "trace-id"
}
```

### 4.2 `POST /conversations`

用途：

- 创建一个新的聊天会话

成功响应：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "id": "uuid",
    "title": "新聊天",
    "scope": "inbox",
    "status": "active",
    "last_message_at": null,
    "updated_at": "2026-04-22T10:00:00Z",
    "last_message_preview": ""
  },
  "request_id": "trace-id"
}
```

### 4.3 `GET /conversations/inbox`

用途：

- 返回当前用户的默认容器与首个会话
- 仅作为兼容接口保留，聊天前端不再主依赖

成功响应：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "conversation": {
      "id": "uuid",
      "title": "默认收件箱会话",
      "status": "active",
      "summary": "",
      "last_message_at": "2026-04-22T10:00:00Z"
    },
    "current_session": {
      "id": "uuid",
      "title": "默认研究讨论",
      "scope": "inbox",
      "status": "active",
      "last_message_at": "2026-04-22T10:00:00Z"
    }
  },
  "request_id": "trace-id"
}
```

### 4.4 `GET /conversations/{id}/messages`

用途：

- 返回会话消息历史

查询参数：

- `before`: 可选，消息游标
- `limit`: 可选，默认 `50`，最大 `100`

成功响应：

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "items": [
      {
        "id": "uuid",
        "role": "assistant",
        "message_type": "chat",
        "content": "你好，我们先收束一下研究目标。",
        "metadata": {},
        "citations": [],
        "created_at": "2026-04-22T10:00:00Z"
      }
    ],
    "paging": {
      "before": "uuid",
      "limit": 50,
      "has_more": false
    }
  },
  "request_id": "trace-id"
}
```

### 4.5 `POST /conversations/{id}/messages/stream`

用途：

- 单请求完成：
  - 用户消息落库
  - LangGraph 聊天图执行
  - SSE 事件回传
  - assistant 最终消息落库

请求体：

```json
{
  "content": "请帮我梳理论文问答工作台的研究方向",
  "client_message_id": "client-uuid",
  "attachment_ids": ["knowledge-file-id-1"],
  "metadata": {}
}
```

后端内部链路：

1. `load_context`
2. `maybe_retrieve_context`
3. `call_model`

内部流来源：

- `graph.astream(..., stream_mode=["messages", "updates", "custom"], version="v2")`

对前端暴露的 SSE 业务事件：

#### `message.started`

```json
{
  "event": "message.started",
  "data": {
    "conversation_id": "uuid",
    "session_id": "uuid",
    "client_message_id": "client-uuid"
  }
}
```

#### `message.delta`

```json
{
  "event": "message.delta",
  "data": {
    "delta": "这是新生成的一段文本",
    "accumulated": "这是当前累计内容"
  }
}
```

#### `message.progress`

```json
{
  "event": "message.progress",
  "data": {
    "stage": "context",
    "node": "maybe_retrieve_context",
    "status": "completed",
    "detail": "当前无额外上下文检索"
  }
}
```

#### `message.tool`

```json
{
  "event": "message.tool",
  "data": {
    "status": "started",
    "tool": "context_loader",
    "detail": "正在整理当前会话上下文"
  }
}
```

`status` 允许值：

- `started`
- `completed`
- `failed`

#### `message.info`

```json
{
  "event": "message.info",
  "data": {
    "detail": "已加载 5 条相关资料"
  }
}
```

#### `message.completed`

```json
{
  "event": "message.completed",
  "data": {
    "message": {
      "id": "uuid",
      "role": "assistant",
      "message_type": "chat",
      "content": "最终完整回复",
      "metadata": {},
      "citations": [],
      "created_at": "2026-04-22T10:00:10Z"
    }
  }
}
```

#### `message.failed`

```json
{
  "event": "message.failed",
  "data": {
    "code": "CHAT_STREAM_FAILED",
    "message": "模型生成失败"
  }
}
```

#### `ping`

```json
{
  "event": "ping",
  "data": {
    "ts": "2026-04-22T10:00:05Z"
  }
}
```

实现约束：

- 用户消息先落库
- assistant 消息不做占位消息更新
- 仅在 `message.completed` 后写正式 assistant 消息
- 若流失败，不写半成品 assistant 消息
- 引用依据仅在 `message.completed` 后写入 `citation_evidences`
- 记忆范围仅限当前会话：
  - 短期记忆来自最近消息窗口
  - 长期记忆来自当前会话摘要

## 5. Task Events

### 5.1 `GET /tasks/{id}/events`

用途：

- 订阅研究任务进度流

实现策略：

1. API 连接建立后先读取数据库并发送 `task.snapshot`
2. 再桥接 Redis Pub/Sub 实时事件

SSE 事件：

#### `task.snapshot`

```json
{
  "event": "task.snapshot",
  "data": {
    "task_id": "uuid",
    "status": "running",
    "current_node": "reading_agent_node",
    "progress_percent": 40.0
  }
}
```

#### 其他事件

- `task.created`
- `task.node.started`
- `task.node.completed`
- `task.node.failed`
- `task.progress`
- `task.completed`
- `task.failed`
- `task.canceled`

统一事件载荷建议包含：

- `task_id`
- `status`
- `current_node`
- `progress_percent`
- `detail`
- `occurred_at`

## 6. 分页约定

### 6.1 列表资源

适用：

- `GET /workspaces`
- `GET /tasks`
- `GET /knowledge`

查询参数：

- `page`: 默认 `1`
- `page_size`: 默认 `20`，最大 `100`

返回结构：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "has_more": false
}
```

### 6.2 时间线资源

适用：

- `GET /conversations/{id}/messages`

查询参数：

- `before`
- `limit`

## 7. 错误码

首批稳定错误码：

- `OK`
- `AUTH_INVALID_CREDENTIALS`
- `AUTH_SESSION_EXPIRED`
- `AUTH_FORBIDDEN`
- `CHAT_CONVERSATION_NOT_FOUND`
- `CHAT_MESSAGE_TOO_LARGE`
- `CHAT_STREAM_FAILED`
- `WORKSPACE_NOT_FOUND`
- `KNOWLEDGE_FILE_TOO_LARGE`
- `KNOWLEDGE_UNSUPPORTED_TYPE`
- `TASK_NOT_FOUND`
- `TASK_INVALID_STATE`
- `INTERNAL_ERROR`

建议 HTTP 映射：

- `400`: 参数错误
- `401`: 未登录或会话失效
- `403`: 无权限
- `404`: 资源不存在
- `409`: 状态冲突
- `413`: 文件或消息体过大
- `500`: 内部错误

## 8. 前端接入约定

- 普通 JSON API：axios + `withCredentials: true`
- SSE：`@microsoft/fetch-event-source` + `credentials: "include"`
- 前端启动流程：
  1. 调 `GET /me`
  2. 成功则恢复登录态
  3. 失败则跳转登录页
- 聊天发送流程：
  1. 本地创建 assistant draft
  2. 消费 `message.delta`
  3. `message.completed` 后用正式消息替换 draft
  4. `message.failed` 时清理 draft 并提示错误
