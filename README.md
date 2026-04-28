# PaperChatAgent

PaperChatAgent 是一个聊天优先的科研 Agent 工作台，面向论文阅读、研究方向澄清、资料沉淀、工具调用和长链路研究任务执行。

它把聊天作为主入口，把知识库 RAG、MCP 工具、Agent Skill、智能体工作流、模型路由和后台任务统一接入到同一套能力调度层中。用户可以像普通聊天一样提出问题，系统会在回复前自动判断是否需要检索知识库、加载 Skill、调用 MCP 工具或启动研究型智能体。

## 核心痛点

- 论文、笔记、网页、会议文档和聊天记录分散，研究上下文容易丢失。
- 普通聊天式 AI 更适合单轮问答，难以持续推进“检索 -> 阅读 -> 分析 -> 写作”的长链路任务。
- RAG、MCP、Skills、智能体工作流通常彼此割裂，用户很难在自然语言对话中调度这些能力。
- 本地或外部工具能力缺少统一的可视化管理、执行日志和聊天回流机制。

## 当前能力

### 聊天主链路

- 登录后默认进入聊天工作台。
- 支持会话记忆、用户长期记忆和上下文加载。
- 聊天流通过 SSE 返回进度、工具调用事件和最终回答。
- 回复前会进入 capability routing 阶段，按需调用 RAG、Skill、MCP 或 Agent 能力。
- 工具结果会显示在回答气泡顶部，并作为上下文注入最终模型回复。

### Capability 能力调度

项目内置统一能力注册与执行层：

- `rag.retrieve`：从知识库检索论文、片段或结构化研究材料。
- `skill.<id>`：加载真实 `SKILL.md` 和参考文件，让聊天按指定 Skill 流程工作。
- `mcp.<server>.<tool>`：调用已注册的 MCP 外部工具。
- `agent.workflow.<slug>`：为后续长周期智能体工作流保留统一入口。

这层设计让后续新增 MCP 工具、RAG 工具、智能体工具或领域专用 Skill 时，不需要重写聊天链路，只需要注册为 capability。

### Agent Skill

Skills 已重构为类似 Codex / AgentChat 的虚拟文件夹模型：

- 支持从本地导入 `~/.agents/skills`、`~/.codex/skills`、`~/.claude/skills`、`~/.cc-switch/skills`。
- 每个 Skill 保存完整文件树，包括 `SKILL.md`、`reference(s)/`、`scripts/`。
- 前端支持查看文件树、编辑 `SKILL.md`、编辑参考文件、新增文件、删除文件。
- 支持自定义创建 Skill。
- 导入和编辑时会做去重：同名 Skill 只能存在一个，同内容 Skill 不能重复导入。
- 聊天中可以通过 `$skill-name`、`@skill-name`，或“用/调用/加载某个 Skill”的自然语言触发。

### MCP 服务

- 支持配置本地 MCP 服务。
- 支持刷新工具列表、查看工具 schema。
- 已加入 MCP runtime，用于在聊天能力路由中执行 MCP 工具。

### 知识库与 RAG

- 管理知识库、文件和解析结果。
- 支持资料上传、arXiv 导入和知识库绑定。
- RAG 检索能力已接入 capability 层，可被聊天按需调用。

### 智能体工作流

- 当前内置研究工作流骨架。
- 工作流节点包括 `search -> reading -> analyse -> writing -> report`。
- 分析子链包括 `cluster_agent -> deep_analyse_agent -> global_analyse_agent`。
- 写作子链包括 `writing_director_agent -> retrieval_agent -> writing_agent -> review_agent`。
- 后台任务页用于展示长链任务进度和节点状态。

## 核心逻辑流

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

## 最新截图

### 聊天工作台

![Chat Capability Workbench](images/current/chat-capability-workbench.png)

### Agent Skill 列表

![Agent Skill List](images/current/skills-list.png)

### Skill 内容编辑

![Agent Skill Editor](images/current/skills-editor.png)

历史线框图仍保留在 [images/light-main](images/light-main)。

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

## 当前后端资源

- `Auth`：注册、登录、刷新、恢复登录态
- `Conversations`：会话列表、消息列表、SSE 聊天流
- `Capabilities`：统一列出和执行 RAG、MCP、Skill、Agent 能力
- `Knowledge`：知识库、文件、解析状态、arXiv 导入
- `RAG`：知识库检索和检索日志
- `MCP`：服务配置、工具发现、工具执行
- `Skills`：导入、创建、编辑、文件 CRUD、聊天触发
- `Agents`：工作流定义、节点定义、运行状态
- `Tasks`：后台任务列表、任务详情、任务事件流
- `Models`：模型提供方、模型路由和调用记录
- `Dashboard`：任务、模型和工具调用观测指标

## 运行方式

### 前端

```bash
cd apps/frontend
pnpm install
pnpm dev
```

默认访问地址：

- `http://localhost:5173`

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

## 目录概览

```text
PaperChatAgent/
├── apps/
│   ├── frontend/          # Vue 3 前端
│   └── backend/           # FastAPI 后端
├── docs/                  # 产品与技术文档
├── designs/               # 设计稿
├── images/                # 页面截图与历史线框图
├── sql/                   # 初始化 SQL
├── README.md
├── 需求文档.md
└── requirements.md
```

## 文档索引

- [中文需求文档](需求文档.md)
- [English Requirements](requirements.md)
- [架构文档](docs/architecture.md)
- [技术方案](docs/technical-design.md)
- [数据模型](docs/data-model.md)
- [数据库设计](docs/database-schema.md)
- [API Contract V1](docs/api-contract-v1.md)
- [开发启动文档](docs/dev-start.md)
- [开发规范](CONTRIBUTING.md)

## 后续重点

- 将智能体工作流的各节点执行与任务恢复机制继续补齐。
- 扩展更多 MCP 工具和领域 Skill。
- 完善知识库解析、切片、向量化和检索效果评估。
- 给能力调用增加更完整的权限、安全确认和可观测性。
