# PaperChatAgent

PaperChatAgent 是一个聊天优先的研究助手。
它把聊天作为用户主链路，把知识库、智能体、MCP、Skills、模型配置、后台任务和数据看板组织为独立模块，用来支撑“研究方向澄清、资料沉淀、工具调用、异步研究执行、结果回流问答”这条连续体验。

当前仓库处于“文档重构 + 前后端骨架联调”阶段：

- 新文档已经统一为“聊天主链路 + 模块化能力”口径
- 前端已具备聊天、知识库、智能体、后台任务的基础页面骨架
- 后端已实现认证、会话、聊天流、知识资料、任务、工作流节点等基础接口
- 研究工作流已落地为 `LangGraph + AutoGen` 的多节点骨架
- 进程内异步任务、节点级恢复骨架、向量检索闭环、MCP / Skills / 模型 / 看板页面仍在后续完善范围

## 当前定位

PaperChatAgent 当前采用以下产品定位：

- `聊天` 是唯一主入口
- `会话` 是用户长期使用的主对象
- `知识库` 是独立资料模块，负责文档解析、切片、向量化和检索来源管理
- `智能体` 是独立能力模块，当前内置一个多节点研究工作流，并保留后续扩展空间
- `MCP 服务` 与 `Skills` 是独立配置模块，面向外部工具能力接入
- `模型` 是独立模块，负责模型配置与模型路由
- `后台任务` 主要展示智能体 / 工作流的执行进度
- `数据看板` 展示模型调用、输入输出量、任务分布等观测指标

## 核心模块

### 聊天

- 登录后的默认入口
- 承载研究目标澄清、资料上传、继续追问
- 右侧提供动态研究提示，可根据当前对话判断是否适合转入深入研究
- 模型可自主判断是否检索知识库、是否调用智能体 / MCP / Skills

### 知识库

- 管理按名称组织的知识库、文件和解析结果
- 支持“知识库列表页 + 知识库详情页”两层结构
- 支持 PDF 上传、资料沉淀、向量检索准备
- 主要在聊天阶段被模型按需使用，而不是作为主入口

### 智能体

- 展示内置智能体、自定义智能体和项目子 Agent
- 支持“智能体列表页 + 智能体详情页”两层结构
- 详情页可为节点配置模型、执行器和上下游传递规则
- 后续可扩展更多智能体、工作流或编排模板

### MCP 服务

- 展示当前配置的 MCP 服务
- 支持导入本地 MCP 服务
- 支持新增 MCP 服务配置

### Skills

- 展示当前配置的 Skills
- 支持导入本地 Skills
- 支持新增自定义 Skills

### 模型

- 展示模型配置与逻辑路由槽位
- 管理 `conversation / tool_call / reasoning / embedding / rerank` 等模型能力

### 后台任务

- 展示主题确认后的异步研究任务
- 重点呈现智能体 / 工作流节点进度、状态和结果摘要

### 数据看板

- 展示模型调用次数、输入输出量、任务运行分布等指标
- 用于系统观测，不是运营后台

## 主链路

当前主链路统一为：

`登录 -> 聊天 -> 澄清研究主题 / 上传文档 -> 绑定或创建知识库 -> 模型自主判断是否检索 -> 按需调用智能体 / MCP / Skills -> 主题确认后触发后台任务 -> 后台任务页展示智能体进度 -> 结果回流聊天继续问答`

## 当前实现状态

### 已完成

- 中文 / 英文需求文档
- 架构、技术方案、数据模型、数据库设计、API 契约、开发启动文档
- MySQL 初始化脚本
- 前端聊天、知识库、智能体、后台任务页面骨架
- FastAPI 后端应用入口、配置加载、数据库初始化
- 认证、会话、聊天流、知识资料、任务、工作流节点相关 API
- LangChain 聊天图与会话级摘要能力
- 多节点研究工作流骨架与任务进度回传

### 进行中

- 向量检索与知识库闭环接入
- 资料解析、切片、向量化的完整异步链路
- 后台任务与工作流节点运行的正式持久化
- 模型模块、MCP 模块、Skills 模块、数据看板模块的真实页面与接口

### 过渡说明

- 当前代码中仍保留部分旧命名，例如 `WorkbenchLayout`、`paperchat_workspaces`
- 这些命名属于实现过渡状态，不再代表新的产品主叙事
- 新文档统一使用“聊天 / 会话 / 模块”口径

## 页面预览

### 当前已出图页面

登录页
![Login](/Users/sdybdc/Code/AICode/PaperChatAgent/images/light-main/auth-login-wireframe.png)

注册页
![Register](/Users/sdybdc/Code/AICode/PaperChatAgent/images/light-main/auth-register-wireframe.png)

聊天页
![Chat](/Users/sdybdc/Code/AICode/PaperChatAgent/images/light-main/chat-research-guidance-wireframe.png)

知识库列表页
![Knowledge](/Users/sdybdc/Code/AICode/PaperChatAgent/images/light-main/knowledge-base-list-wireframe.png)

知识库详情页
![Knowledge Detail](/Users/sdybdc/Code/AICode/PaperChatAgent/images/light-main/knowledge-base-detail-wireframe.png)

MCP 服务页
![MCP](/Users/sdybdc/Code/AICode/PaperChatAgent/images/light-main/mcp-services-wireframe.png)

Skills 页
![Skills](/Users/sdybdc/Code/AICode/PaperChatAgent/images/light-main/skills-management-wireframe.png)

智能体列表页
![Agents](/Users/sdybdc/Code/AICode/PaperChatAgent/images/light-main/agents-list-wireframe.png)

智能体详情页
![Agents Detail](/Users/sdybdc/Code/AICode/PaperChatAgent/images/light-main/agents-detail-configuration-wireframe.png)

模型页
![Models](/Users/sdybdc/Code/AICode/PaperChatAgent/images/light-main/model-routing-wireframe.png)

后台任务页
![Tasks](/Users/sdybdc/Code/AICode/PaperChatAgent/images/light-main/background-tasks-wireframe.png)

数据看板页
![Dashboard](/Users/sdybdc/Code/AICode/PaperChatAgent/images/light-main/dashboard-overview-wireframe.png)

## 技术栈

### 前端

- Vue 3
- Vite
- Vue Router
- Pinia
- Element Plus
- Axios

### 后端

- FastAPI
- LangChain
- LangGraph
- AutoGen
- MySQL
- MinIO
- ChromaDB

## 当前后端能力

`apps/backend` 当前已实现的资源能力包括：

- `Auth`：注册、登录、刷新、恢复登录态
- `Conversations`：会话列表、消息列表、SSE 聊天流
- `Knowledge`：资料上传、arXiv 导入、资料挂接占位
- `Agents`：默认工作流定义、节点定义、按任务查看节点运行态
- `Tasks`：任务创建、任务列表、任务详情、任务报告、任务事件流

当前研究工作流骨架采用：

- 外层：`LangGraph`
- 节点：`search -> reading -> analyse -> writing -> report`
- 分析子链：`cluster_agent -> deep_analyse_agent -> global_analyse_agent`
- 写作子链：`writing_director_agent -> retrieval_agent -> writing_agent -> review_agent`

## 文档索引

### 产品与设计

- [中文需求文档](/Users/sdybdc/Code/AICode/PaperChatAgent/需求文档.md)
- [English Requirements](/Users/sdybdc/Code/AICode/PaperChatAgent/requirements.md)
- [Pencil MCP 接入说明](/Users/sdybdc/Code/AICode/PaperChatAgent/docs/pencil-mcp-setup.md)

### 架构与实现

- [架构文档](/Users/sdybdc/Code/AICode/PaperChatAgent/docs/architecture.md)
- [技术方案](/Users/sdybdc/Code/AICode/PaperChatAgent/docs/technical-design.md)
- [数据模型](/Users/sdybdc/Code/AICode/PaperChatAgent/docs/data-model.md)
- [数据库设计](/Users/sdybdc/Code/AICode/PaperChatAgent/docs/database-schema.md)
- [API Contract V1](/Users/sdybdc/Code/AICode/PaperChatAgent/docs/api-contract-v1.md)
- [开发启动文档](/Users/sdybdc/Code/AICode/PaperChatAgent/docs/dev-start.md)
- [开发规范](/Users/sdybdc/Code/AICode/PaperChatAgent/CONTRIBUTING.md)

## 运行方式

### 前端

```bash
cd apps/frontend
pnpm install
pnpm dev
```

默认访问地址：

- `http://127.0.0.1:5173`

### 后端

```bash
cd apps/backend
uv sync
cp paperchat/config.example.yaml paperchat/config.yaml
uv run uvicorn paperchat.main:app --host 127.0.0.1 --port 8000 --reload
```

默认地址：

- API：`http://127.0.0.1:8000/api/v1`
- Swagger：`http://127.0.0.1:8000/swagger`

### 后台任务执行

当前版本的后台任务采用 Python 进程内异步任务实现，而不是独立 worker。
当前恢复机制已经按以下方向设计：

- 节点自动重试
- 节点失败后自动暂停任务
- 支持从失败节点续跑
- 支持备用模型切换策略
- 支持节点 checkpoint 持久化

## 目录概览

```text
PaperChatAgent/
├── apps/
│   ├── frontend/          # Vue 3 前端
│   └── backend/           # FastAPI 后端
├── docs/                  # 产品与技术文档
├── designs/               # 设计稿
├── images/                # 页面预览图
├── sql/                   # 初始化 SQL
├── README.md
├── 需求文档.md
└── requirements.md
```

## 后续重点

- 打通知识库解析、切片、向量化与检索
- 增加模型模块、MCP 模块、Skills 模块、数据看板模块
- 将后台任务页与智能体节点运行态做完整真实联调
- 把当前实现中的旧命名逐步迁移到新的“聊天 / 会话 / 模块”语义
