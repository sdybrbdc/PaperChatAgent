# PaperChatAgent 技术方案文档

## 1. 文档目标

本文档用于冻结 PaperChatAgent V1 的技术方案、模块边界、接口语义和实现约束，使工程实现能够稳定围绕“聊天主链路 + 模块化能力”展开。

## 2. 设计原则

### 2.1 聊天优先

- 聊天是唯一主链路
- 会话是前后端的主对象
- 其他模块都围绕聊天提供能力，而不是与聊天争夺主入口

### 2.2 模块独立

- 知识库独立负责资料解析与检索来源管理
- 智能体独立负责工作流定义与能力扩展
- MCP / Skills 独立负责工具配置
- 模型模块独立负责配置与路由
- 后台任务独立负责展示工作流执行进度

### 2.3 文档与实现分层

- 文档先冻结目标语义
- 当前实现中的旧命名与兼容结构必须单独标注为“过渡状态”
- 不再让旧的“工作台 / 工作区”叙事污染新方案

## 3. 技术基线

### 3.1 前端

- Vue 3
- Vite
- Vue Router
- Pinia
- Element Plus
- Axios

### 3.2 后端

- FastAPI
- LangChain
- LangGraph
- AutoGen
- SQLAlchemy

### 3.3 数据与运行时

- MySQL
- MinIO
- ChromaDB
- Python `asyncio`

## 4. 前端方案

### 4.1 路由模块

目标前端路由如下：

- `/chat`
- `/knowledge`
- `/agents`
- `/mcp`
- `/skills`
- `/models`
- `/tasks`
- `/dashboard`

说明：

- 当前仓库已实现 `chat / knowledge / agents / tasks`
- `mcp / skills / models / dashboard` 为下一阶段扩展模块

### 4.2 页面职责

#### Chat Page

- 会话列表
- 消息列表
- 输入框与上传入口
- 流式响应展示
- 动态研究提示与研究草案入口

#### Knowledge Page

- 知识库列表页
- 知识库详情页
- 文件列表与解析 / 索引状态
- 上传与导入入口

#### Agents Page

- 智能体列表页
- 智能体详情页
- 节点级模型 / 执行器配置
- 项目子 Agent 与自定义 Agent 扩展

#### Tasks Page

- 任务列表
- 当前节点
- 节点进度
- 运行状态与结果摘要

#### Models / MCP / Skills / Dashboard

- 作为独立模块管理配置或展示指标
- 不承担聊天主链路

### 4.3 Pinia Store 建议

- `authStore`
- `conversationStore`
- `knowledgeStore`
- `agentsStore`
- `taskStore`
- `modelStore`
- `mcpStore`
- `skillsStore`
- `dashboardStore`
- `uiStore`

## 5. 后端方案

### 5.1 服务拆分

建议采用以下服务边界：

- `auth service`
- `chat service`
- `knowledge service`
- `agent registry service`
- `mcp registry service`
- `skill registry service`
- `model router service`
- `task service`
- `dashboard service`
- `storage service`

### 5.2 API 风格

V1 采用：

- `REST` 作为资源接口
- `SSE` 作为聊天流和任务进度流

不采用：

- 以 WebSocket 为默认协议
- 以 GraphQL 为主资源接口

### 5.3 DTO 原则

前后端必须围绕稳定 DTO 开发，组件层不能直接依赖底层表字段。

建议首批 DTO：

- `CurrentUserDTO`
- `ChatSessionDTO`
- `MessageDTO`
- `KnowledgeBaseDTO`
- `KnowledgeFileDTO`
- `ResearchTaskDTO`
- `WorkflowRunDTO`
- `WorkflowNodeRunDTO`
- `AgentWorkflowDTO`
- `McpServerConfigDTO`
- `SkillConfigDTO`
- `ModelRouteConfigDTO`
- `DashboardOverviewDTO`

## 6. 聊天编排方案

### 6.1 主职责

聊天服务负责：

- 读取会话上下文
- 读取会话级长期摘要
- 判断当前可用知识库
- 交给模型决定是否检索或调用工具
- 把结果通过 SSE 回传给前端

### 6.2 推荐执行链

聊天服务推荐链路如下：

1. `load_session_context`
2. `load_bound_knowledge`
3. `decide_retrieval_or_tool_use`
4. `run_retrieval_if_needed`
5. `run_tool_calls_if_needed`
6. `call_model`
7. `persist_messages`

说明：

- 模型不是每轮都必须检索知识库
- 模型不是每轮都必须调用智能体 / MCP / Skills
- 这些行为由聊天阶段上下文和模型判断共同决定

### 6.3 SSE 事件

聊天 SSE 继续采用：

- `message.started`
- `message.delta`
- `message.progress`
- `message.tool`
- `message.info`
- `message.completed`
- `message.failed`
- `ping`

`message.tool` 可用于表示：

- 知识检索
- 智能体调用
- MCP 调用
- Skill 调用

### 6.4 当前实现差异

当前代码中的聊天图仍然更接近：

- `load_context`
- `maybe_retrieve_context`
- `call_model`

它尚未完整实现自主工具路由，但文档口径以目标链路为准。

## 7. 知识库方案

### 7.1 模块职责

知识库负责：

- 知识库创建与命名
- 文件上传与导入
- 文档解析
- 文本切片
- 向量化
- 检索来源管理

### 7.2 资料进入方式

- 用户在知识库页面手动创建并上传
- 用户在聊天阶段上传资料并绑定到已有知识库
- 系统在聊天中建议创建新知识库，用户确认后自动落库

### 7.3 检索策略

- 检索不是强制前置动作
- 模型在聊天中自主判断是否需要检索
- 检索结果只作为回答辅助上下文，而不是替代聊天

## 8. 智能体方案

### 8.1 模块职责

智能体模块负责：

- 注册当前可用智能体 / 工作流
- 暴露工作流定义与节点说明
- 提供给聊天与任务系统可调用的能力对象

### 8.2 当前默认工作流

当前内置工作流为多节点研究工作流，包含：

- `search`
- `reading`
- `analyse`
- `writing`
- `report`

### 8.3 运行方式

智能体能力可通过两种方式被消费：

- 在聊天阶段作为工具被调用
- 在研究任务阶段作为异步工作流执行

### 8.4 扩展性

后续允许新增：

- 其他研究工作流
- 更轻量的专用智能体
- 不同场景的工具型智能体

## 9. MCP 与 Skills 方案

### 9.1 MCP 服务

MCP 模块负责：

- 列表展示当前 MCP 配置
- 导入本地 MCP 服务
- 新增 MCP 服务配置

### 9.2 Skills

Skills 模块负责：

- 列表展示当前 Skill 配置
- 导入本地 Skills
- 新增自定义 Skills

### 9.3 与聊天关系

- MCP / Skills 都是聊天阶段可能调用的能力
- 它们不是单独主链路
- 它们的配置和调用结果必须与聊天层解耦

## 10. 模型模块方案

### 10.1 模块职责

模型模块负责：

- 管理供应商与模型配置
- 管理逻辑模型槽位
- 将业务请求路由到对应模型

### 10.2 逻辑模型槽位

至少包含：

- `conversation`
- `tool_call`
- `reasoning`
- `embedding`
- `rerank`

根据需要可继续扩展：

- `vision`
- `text2image`

### 10.3 配置建议

配置文件应至少包含：

- `provider`
- `base_url`
- `api_key`
- `model_name`
- `timeout`
- `metadata`

### 10.4 设计边界

模型模块不负责：

- 业务状态管理
- 会话管理
- 任务调度

## 11. 后台任务方案

### 11.1 页面职责

后台任务模块的职责不是“通用任务管理”，而是：

- 展示研究任务
- 展示工作流运行
- 展示节点进度
- 展示结果摘要

### 11.2 状态模型

任务状态建议：

- `queued`
- `running`
- `paused`
- `completed`
- `failed`
- `canceled`

节点状态建议：

- `pending`
- `running`
- `retrying`
- `paused`
- `completed`
- `failed`
- `skipped`

### 11.3 当前执行方式

当前版本采用 Python 进程内异步任务：

- 通过 `asyncio.create_task(...)` 启动研究任务
- 不引入独立 Worker + 队列
- 节点级状态和 checkpoint 持久化到 MySQL JSON 字段

### 11.4 恢复机制

当前版本的恢复机制必须具备：

- 自动重试：单节点失败后先按策略自动重试
- 备用模型切换：主模型失败后尝试备用模型覆盖
- 节点暂停：所有尝试都失败后，将任务停在当前节点
- 从失败节点续跑：支持恢复当前节点并继续后续节点
- checkpoint 持久化：每个节点的输入、输出、错误、尝试次数和工作流状态都落库

### 11.5 SSE 事件

任务事件继续采用：

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

## 12. 数据看板方案

### 12.1 指标范围

首批看板指标建议包括：

- 模型调用次数
- 输入 token
- 输出 token
- 任务总数
- 任务状态分布
- 工作流节点平均耗时

### 12.2 数据来源

看板数据可来自：

- 请求日志
- 模型调用日志
- 任务运行日志
- 聚合后的统计表或物化视图

## 13. 配置方案

配置文件建议包含以下段：

- `server`
- `mysql`
- `storage`
- `vector_db`
- `model_routes`
- `mcp`
- `skills`

## 14. 当前实现兼容说明

当前代码与目标文档之间存在以下过渡差异：

- 当前前端页面仍沿用部分 `workbench` 命名
- 当前后端仍保留 `workspace` 相关表结构
- `knowledge_bases`、`mcp`、`skills`、`models`、`dashboard` 等模块尚未完整落地为真实 API
- 当前任务执行明确采用应用进程内异步运行器

这些差异都属于实现过渡期，不改变目标产品和技术口径。

## 15. 结论

PaperChatAgent V1 的技术方案可以概括为：

- 以会话为主对象
- 以聊天为总调度入口
- 以知识库、智能体、MCP、Skills、模型、后台任务、看板作为独立模块
- 以模型自主决策检索与工具调用
- 以后台任务页持续展示智能体执行进度
