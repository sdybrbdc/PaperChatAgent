# PaperChatAgent

PaperChatAgent 是一个聊天优先的研究助手。
它把聊天作为用户主链路，把知识库、智能体、MCP、Skills、模型配置、后台任务和数据看板组织为独立模块，用来支撑“研究方向澄清、资料沉淀、工具调用、异步研究执行、结果回流问答”这条连续体验。

当前仓库已经从“文档重构 + 前后端骨架联调”推进到“聊天主链路 + 模块化能力接入”的阶段：

- 新文档已经统一为“聊天主链路 + 模块化能力”口径
- 前端已具备聊天、知识库、MCP、Skills、智能体、模型、后台任务和数据看板页面
- 后端已实现认证、会话、聊天流、知识资料、RAG、MCP、Skills、模型、任务、工作流节点等基础接口
- 研究工作流已落地为 `LangGraph + AutoGen` 的多节点骨架
- 聊天链路已接入统一 `Capability` 能力路由，可按需调用 RAG、MCP、Skills 和后续 Agent 工具
- Skills 已支持类似 Codex / AgentChat 的本地 Skill 导入、内容查看、文件编辑、自定义创建、删除和聊天触发
- MCP 已支持服务配置、工具发现、工具 schema 查看和 runtime 执行
- 资料解析、切片、向量化、智能体节点恢复和更完整的权限确认仍在持续完善

## 核心痛点

- 论文、笔记、网页、会议文档和聊天记录分散，研究上下文容易丢失。
- 普通聊天式 AI 更适合单轮问答，难以持续推进“检索 -> 阅读 -> 分析 -> 写作”的长链路任务。
- RAG、MCP、Skills、智能体工作流通常彼此割裂，用户很难在自然语言对话中统一调度这些能力。
- 本地或外部工具能力缺少统一的可视化管理、执行日志和聊天回流机制。

## 当前定位

PaperChatAgent 当前采用以下产品定位：

- `聊天` 是唯一主入口
- `会话` 是用户长期使用的主对象
- `知识库` 是独立资料模块，负责文档解析、切片、向量化和检索来源管理
- `智能体` 是独立能力模块，当前内置一个多节点研究工作流，并保留后续扩展空间
- `MCP 服务` 与 `Skills` 是独立配置模块，面向外部工具能力接入
- `Capability` 是聊天前的统一能力路由层，把 RAG、MCP、Skills 和 Agent 工具接入同一执行入口
- `模型` 是独立模块，负责模型配置与模型路由
- `后台任务` 主要展示智能体 / 工作流的执行进度
- `数据看板` 展示模型调用、输入输出量、任务分布等观测指标

## 核心模块

### 聊天

- 登录后的默认入口
- 承载研究目标澄清、资料上传、继续追问
- 支持短期会话记忆和用户长期记忆上下文加载
- 右侧提供动态研究提示，可根据当前对话判断是否适合转入深入研究
- SSE 流式返回消息进度、工具调用事件和最终回答
- 模型可自主判断是否检索知识库、是否调用智能体 / MCP / Skills
- 工具结果会显示在回答气泡顶部，并作为上下文注入最终模型回复

### Capability 能力调度

项目内置统一能力注册与执行层：

- `rag.retrieve`：从项目知识库检索论文、片段或结构化研究材料
- `skill.<id>`：加载真实 `SKILL.md` 和参考文件，让聊天按指定 Skill 流程工作
- `mcp.<server>.<tool>`：调用已注册的 MCP 外部工具
- `agent.workflow.<slug>`：为后续长周期智能体工作流保留统一入口

这层设计让后续新增 MCP 工具、RAG 工具、智能体工具或领域专用 Skill 时，不需要重写聊天链路，只需要注册为 capability。

### 知识库

- 管理按名称组织的知识库、文件和解析结果
- 支持“知识库列表页 + 知识库详情页”两层结构
- 支持 PDF 上传、arXiv 导入、资料沉淀、向量检索准备
- RAG 检索能力已接入 capability 层，可被聊天按需调用
- 主要在聊天阶段被模型按需使用，而不是作为主入口

### 智能体

- 展示内置智能体、自定义智能体和项目子 Agent
- 支持“智能体列表页 + 智能体详情页 + 运行详情页”结构
- 详情页可为节点配置模型、执行器和上下游传递规则
- 当前内置研究工作流骨架：`search -> reading -> analyse -> writing -> report`
- 后续可扩展更多智能体、工作流或编排模板

### MCP 服务

- 展示当前配置的 MCP 服务
- 支持导入本地 MCP 服务
- 支持新增 MCP 服务配置
- 支持刷新工具列表、查看工具 schema
- 已加入 MCP runtime，用于在聊天能力路由中执行 MCP 工具

### Skills

Skills 已重构为类似 Codex / AgentChat 的虚拟文件夹模型：

- 展示当前配置的 Skills
- 支持从本地导入 `~/.agents/skills`、`~/.codex/skills`、`~/.claude/skills`、`~/.cc-switch/skills`
- 支持新增自定义 Skills
- 每个 Skill 保存完整文件树，包括 `SKILL.md`、`reference(s)/`、`scripts/`
- 前端支持查看文件树、编辑 `SKILL.md`、编辑参考文件、新增文件、删除文件
- 导入和编辑时会做去重：同名 Skill 只能存在一个，同内容 Skill 不能重复导入
- 聊天中可以通过 `$skill-name`、`@skill-name`，或“用/调用/加载某个 Skill”的自然语言触发

### 模型

- 展示模型配置与逻辑路由槽位
- 管理 `conversation / tool_call / reasoning / embedding / rerank` 等模型能力
- 为聊天、工具选择、推理、Embedding 和重排保留独立路由

### 后台任务

- 展示主题确认后的异步研究任务
- 重点呈现智能体 / 工作流节点进度、状态和结果摘要
- 支持工作流运行详情和节点状态回看

### 数据看板

- 展示模型调用次数、输入输出量、任务运行分布等指标
- 展示能力调用、工具执行、任务状态等观测指标
- 用于系统观测，不是运营后台

## 主链路

当前主链路统一为：

`登录 -> 聊天 -> 澄清研究主题 / 上传文档 -> 绑定或创建知识库 -> 加载会话记忆和用户记忆 -> Capability 路由判断是否需要 RAG / MCP / Skills / Agent -> 执行工具并回流结果 -> 主题确认后触发后台任务 -> 后台任务页展示智能体进度 -> 结果回流聊天继续问答`

核心逻辑流：

```text
登录
  -> 聊天输入研究问题
  -> 加载短期会话记忆和用户长期记忆
  -> 能力路由判断是否需要 RAG / Skill / MCP / Agent
  -> 执行被选中的能力并记录日志
  -> 将工具结果注入模型上下文
  -> 生成回答
  -> 必要时启动后台研究工作流
  -> 任务进度和产物回流聊天继续追问
```

长链研究任务会继续拆成检索、阅读、聚类、深度分析、全局分析、写作和审阅等阶段。主聊天 Agent 负责理解用户意图和协调能力，RAG、Skill、MCP 与研究工作流分别负责资料检索、领域流程、外部工具和异步任务执行。

## 当前实现状态

### 已完成

- 中文 / 英文需求文档
- 架构、技术方案、数据模型、数据库设计、API 契约、开发启动文档
- MySQL 初始化脚本
- 前端聊天、知识库、MCP、Skills、智能体、模型、后台任务、数据看板页面
- FastAPI 后端应用入口、配置加载、数据库初始化
- 认证、会话、聊天流、知识资料、任务、工作流节点相关 API
- LangChain 聊天图与会话级摘要能力
- 用户长期记忆和短期会话记忆上下文
- 多节点研究工作流骨架与任务进度回传
- Capability 能力注册、路由、执行和日志骨架
- RAG 检索能力接入聊天路由
- MCP 服务配置、工具发现、工具 schema 和 runtime 执行
- Agent Skill 导入、创建、查看、编辑、删除、去重和聊天触发
- README 最新截图与完整功能说明

### 进行中

- 资料解析、切片、向量化的完整异步链路
- 后台任务与工作流节点运行的正式持久化和恢复
- Agent workflow 作为 capability 的完整执行入口
- MCP 工具调用的权限确认、安全拦截和更细粒度错误反馈
- Skill 参考文件按需加载、上下文裁剪和更精确触发策略
- 数据看板与真实运行日志的进一步联动

### 过渡说明

- 当前代码中仍保留部分旧命名，例如 `WorkbenchLayout`
- 这些命名属于实现过渡状态，不再代表新的产品主叙事
- 新文档统一使用“聊天 / 会话 / 模块 / Capability”口径

## 页面预览

### 最新功能截图

聊天工作台
![Chat Capability Workbench](images/current/chat-capability-workbench.png)

Agent Skill 列表
![Agent Skill List](images/current/skills-list.png)

Skill 内容编辑
![Agent Skill Editor](images/current/skills-editor.png)

### 历史线框图

登录页
![Login](images/light-main/auth-login-wireframe.png)

注册页
![Register](images/light-main/auth-register-wireframe.png)

聊天页
![Chat](images/light-main/chat-research-guidance-wireframe.png)

知识库列表页
![Knowledge](images/light-main/knowledge-base-list-wireframe.png)

知识库详情页
![Knowledge Detail](images/light-main/knowledge-base-detail-wireframe.png)

MCP 服务页
![MCP](images/light-main/mcp-services-wireframe.png)

Skills 页
![Skills](images/light-main/skills-management-wireframe.png)

智能体列表页
![Agents](images/light-main/agents-list-wireframe.png)

智能体详情页
![Agents Detail](images/light-main/agents-detail-configuration-wireframe.png)

模型页
![Models](images/light-main/model-routing-wireframe.png)

后台任务页
![Tasks](images/light-main/background-tasks-wireframe.png)

数据看板页
![Dashboard](images/light-main/dashboard-overview-wireframe.png)

## 技术栈

### 前端

- Vue 3
- Vite
- Vue Router
- Pinia
- Element Plus
- Axios
- Fetch Event Source

### 后端

- FastAPI
- LangChain
- LangGraph
- AutoGen
- MySQL
- MinIO
- ChromaDB
- PyYAML

## 当前后端能力

`apps/backend` 当前已实现的资源能力包括：

- `Auth`：注册、登录、刷新、恢复登录态
- `Conversations`：会话列表、消息列表、SSE 聊天流
- `Capabilities`：统一列出和执行 RAG、MCP、Skill、Agent 能力
- `Knowledge`：资料上传、arXiv 导入、资料解析状态、资料挂接占位
- `RAG`：知识库检索和检索日志
- `MCP`：服务配置、工具发现、工具 schema、工具执行
- `Skills`：本地导入、创建、详情、编辑、文件 CRUD、删除、去重、聊天触发
- `Agents`：默认工作流定义、节点定义、运行详情、按任务查看节点运行态
- `Tasks`：任务创建、任务列表、任务详情、任务报告、任务事件流
- `Models`：模型提供方、模型路由和调用记录
- `Dashboard`：任务、模型和工具调用观测指标

当前研究工作流骨架采用：

- 外层：`LangGraph`
- 节点：`search -> reading -> analyse -> writing -> report`
- 分析子链：`cluster_agent -> deep_analyse_agent -> global_analyse_agent`
- 写作子链：`writing_director_agent -> retrieval_agent -> writing_agent -> review_agent`

## 文档索引

### 产品与设计

- [中文需求文档](需求文档.md)
- [English Requirements](requirements.md)
- [Pencil MCP 接入说明](docs/pencil-mcp-setup.md)

### 架构与实现

- [架构文档](docs/architecture.md)
- [技术方案](docs/technical-design.md)
- [数据模型](docs/data-model.md)
- [数据库设计](docs/database-schema.md)
- [API Contract V1](docs/api-contract-v1.md)
- [开发启动文档](docs/dev-start.md)
- [开发规范](CONTRIBUTING.md)

## 运行方式

### 前端

```bash
cd apps/frontend
pnpm install
pnpm dev
```

默认访问地址：

- `http://localhost:5173`
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

## 文件结构

```text
PaperChatAgent/
├── apps/
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── apis/                 # 前端 API 封装
│   │   │   │   ├── agents.ts
│   │   │   │   ├── auth.ts
│   │   │   │   ├── chat.ts
│   │   │   │   ├── dashboard.ts
│   │   │   │   ├── knowledge.ts
│   │   │   │   ├── mcp.ts
│   │   │   │   ├── models.ts
│   │   │   │   ├── skills.ts
│   │   │   │   └── tasks.ts
│   │   │   ├── components/
│   │   │   │   ├── auth/             # 登录注册辅助组件
│   │   │   │   ├── chat/             # 消息气泡、研究提示面板
│   │   │   │   └── shared/           # 侧边栏、空状态等通用组件
│   │   │   ├── layouts/              # AuthLayout / WorkbenchLayout
│   │   │   ├── pages/
│   │   │   │   ├── agents/           # 智能体列表、详情、运行页
│   │   │   │   ├── chat/             # 聊天主入口
│   │   │   │   ├── dashboard/        # 数据看板
│   │   │   │   ├── knowledge/        # 知识库页面
│   │   │   │   ├── login/            # 登录页
│   │   │   │   ├── mcp/              # MCP 服务页
│   │   │   │   ├── models/           # 模型配置页
│   │   │   │   ├── register/         # 注册页
│   │   │   │   ├── skills/           # Agent Skill 列表与编辑器
│   │   │   │   └── tasks/            # 后台任务页
│   │   │   ├── router/               # Vue Router
│   │   │   ├── stores/               # Pinia 状态
│   │   │   ├── types/                # 前端 DTO 类型
│   │   │   ├── utils/                # HTTP 与 SSE 工具
│   │   │   └── style.css             # 全局页面样式
│   │   ├── package.json
│   │   └── vite.config.ts
│   └── backend/
│       ├── paperchat/
│       │   ├── api/
│       │   │   └── v1/               # FastAPI v1 路由
│       │   │       ├── auth.py
│       │   │       ├── capabilities.py
│       │   │       ├── conversations.py
│       │   │       ├── dashboard.py
│       │   │       ├── knowledge.py
│       │   │       ├── mcp.py
│       │   │       ├── models.py
│       │   │       ├── rag.py
│       │   │       ├── skills.py
│       │   │       └── tasks.py
│       │   ├── agents/               # 研究工作流 Agent 实现
│       │   │   └── research_orchestrator/
│       │   ├── auth/                 # JWT、Cookie 与登录态
│       │   ├── database/             # SQLAlchemy 模型、DAO、初始化
│       │   ├── prompts/              # 聊天与 Skill 相关 prompt
│       │   ├── providers/            # 模型供应商适配
│       │   ├── schemas/              # Pydantic 请求 / 响应模型
│       │   ├── services/
│       │   │   ├── agents/           # 智能体工作流服务
│       │   │   ├── capabilities/     # 统一能力注册、执行与日志
│       │   │   ├── cc_switch/        # 本地 cc-switch Skill 发现
│       │   │   ├── chat/             # 聊天流、记忆和能力路由
│       │   │   ├── dashboard/        # 数据看板服务
│       │   │   ├── knowledge/        # 知识库服务
│       │   │   ├── mcp/              # MCP 配置、工具发现与 runtime
│       │   │   ├── model_router/     # 模型提供方与路由
│       │   │   ├── rag/              # RAG 检索服务
│       │   │   ├── skills/           # Agent Skill 虚拟文件夹与 CRUD
│       │   │   ├── storage/          # MinIO / OSS 存储适配
│       │   │   ├── stream/           # SSE 事件翻译
│       │   │   └── tasks/            # 后台任务服务
│       │   ├── workflows/            # LangGraph 工作流
│       │   ├── main.py               # FastAPI 应用入口
│       │   ├── settings.py           # 配置加载
│       │   └── config.example.yaml
│       ├── pyproject.toml
│       └── uv.lock
├── docs/                           # 产品与技术文档
├── designs/                        # 设计稿
├── images/
│   ├── current/                    # 当前真实页面截图
│   │   ├── chat-capability-workbench.png
│   │   ├── skills-editor.png
│   │   └── skills-list.png
│   └── light-main/                 # 历史线框图
├── sql/                            # 初始化 SQL
├── README.md
├── 需求文档.md
└── requirements.md
```

## 后续重点

- 打通知识库解析、切片、向量化与检索的完整生产链路
- 将后台任务页与智能体节点运行态做完整真实联调
- 扩展 MCP 工具、RAG 工具、领域 Skills 和智能体工具
- 给能力调用增加更完整的权限、安全确认和可观测性
- 把当前实现中的旧命名逐步迁移到新的“聊天 / 会话 / 模块 / Capability”语义
