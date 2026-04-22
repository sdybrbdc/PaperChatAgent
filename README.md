# PaperChatAgent

PaperChatAgent 是一个面向科研人员和学生的论文调研工作台。  
它以聊天为入口，以研究工作区为沉淀对象，以研究任务为执行单元，目标是把“研究方向澄清、论文检索、文献阅读、分析归纳、报告产出、结果回流问答”组织成一套可持续使用的工作流。

当前仓库已经进入 **前后端骨架联调阶段**：

- 产品需求、技术文档、数据库设计已成型
- 设计稿已完成白色主主题与两套备选主题
- 前端已搭好白色主主题工作台页面，并接入部分真实后端资源接口
- 后端已实现认证、聊天、任务、知识库、Agents API 与研究工作流骨架
- 研究工作流已落地为 `LangGraph + AutoGen Team` 的五节点实现
- Worker 仍处于占位阶段，尚未接入真实队列消费

## 当前预览

### 白色主主题

登录页  
![Login](images/light-main/login-wireframe.png)

注册页  
![Register](images/light-main/register-wireframe.png)

默认聊天页  
![Chat](images/light-main/home-wireframe.png)

知识库页  
![Knowledge](images/light-main/knowledge-wireframe.png)

智能体页  
![Agents](images/light-main/agents-wireframe.png)

后台任务页  
![Tasks](images/light-main/tasks-wireframe.png)

## 项目目标

PaperChatAgent 当前聚焦以下方向：

- 默认聊天页作为研究入口
- 通过 `默认收件箱会话` 帮用户澄清研究主题
- 在方向明确后创建 `研究工作区`
- 通过后台 `研究任务` 执行完整研究工作流
- 将结果沉淀为 `主题探索包`
- 在后续问答中提供带 `引用依据` 的回答

当前技术路线明确参考两个现有项目：

- `AgentChat`：聊天层、RAG、模型配置、认证与整体后端分层
- `Paper-Agent`：完整论文研究工作流、多智能体节点设计、AutoGen + LangGraph 协作方式

## 核心特性

- 聊天式研究入口：从默认聊天页开始澄清研究方向
- 工作区沉淀：围绕主题长期组织会话、任务、知识和结果
- 双层知识库：账号级全局知识库 + 工作区私有知识库
- 后台任务驱动：研究流程异步执行，前端只负责展示与跟踪
- 完整研究工作流：搜索、阅读、分析、写作、报告、回流问答
- 多智能体子链：分析阶段包含 `cluster / deep_analyse / global_analyse`，写作阶段包含 `writing_director / retrieval / writing / review`
- AutoGen Team 写作协作：章节级写作采用 `SelectorGroupChat + FunctionTool + TextMentionTermination`
- 引用式问答：回答可关联论文与片段级引用依据

## 当前进度

### 已完成

- 中文需求文档与英文需求文档
- 架构文档、技术方案、数据模型、数据库设计、开发启动文档
- MySQL 初始化脚本
- Pencil 设计稿
- 登录页 / 注册页 / 默认聊天页 / 知识库页 / 智能体页 / 后台任务页设计稿
- 前端白色主主题静态实现
- Mock 登录、路由守卫、Pinia 基础状态管理
- FastAPI 后端应用入口、配置加载、数据库初始化
- 认证、会话、聊天流、任务、知识库、工作区、Agents API
- LangChain 聊天图与会话级长期摘要
- 五节点研究工作流：`search -> reading -> analyse -> writing -> report`
- 分析子 Agent 与写作子 Agent 运行时
- AutoGen Team 写作协作链与任务进度回传
- 任务报告产物与节点状态内存态保存

### 未完成

- Worker 真实队列消费与跨进程任务执行
- `workflow_runs / workflow_node_runs / report_artifacts` 等正式持久化表落库
- ChromaDB / 更完整知识库检索接入
- 研究任务中间结果持久化与可回放
- 前端与任务页 / 智能体页 / 聊天页的完整真实联调
- 搜索、阅读、报告节点进一步统一到 AutoGen `run_stream()` 风格
- HITL 人工审核链路接回前端

## V1 核心能力范围

当前 V1 目标页面和能力包括：

- 登录页
- 注册页
- 默认聊天页
- 知识库页
- 智能体页
- 后台任务页

产品主链路：

`登录 -> 默认聊天 -> 澄清需求/上传资料 -> AI 建议研究任务 -> 用户确认 -> 创建工作区 -> 后台执行 -> 结果回流问答`

## 当前阶段说明

当前仓库处于“**前端静态体验 + 后端真实资源骨架**”并行推进阶段：

- 登录页和注册页可直接打开使用
- 登录支持本地 mock，也已具备真实后端认证接口
- 默认聊天、任务、知识库、智能体相关后端接口已经可运行
- 研究任务已能触发真实工作流骨架，而不是纯演示进度条
- 前端仍以工作台体验和联调准备为主，尚未完成全链路真实接入
- 目前不做移动端适配

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
- AutoGen
- LangGraph
- MySQL
- Redis
- MinIO
- ChromaDB

## 当前后端能力

当前 `apps/backend` 已实现以下能力：

- `Auth`：注册、登录、刷新、恢复登录态
- `Conversations`：会话列表、消息列表、SSE 聊天流
- `Tasks`：任务创建、任务列表、任务详情、任务报告、任务事件流
- `Knowledge`：文件上传、arXiv 导入、资料挂接
- `Agents`：默认研究工作流定义、节点定义、按任务查看节点运行态
- `Workflows`：五节点研究工作流和分析/写作子 Agent 运行时

其中研究工作流当前采用：

- 外层：`LangGraph`
- 分析节点：`cluster_agent -> deep_analyse_agent -> global_analyse_agent`
- 写作节点：`writing_director_agent -> SelectorGroupChat(writing_agent, retrieval_agent, review_agent)`

## 文档索引

### 产品与设计

- [需求文档](需求文档.md)
- [Requirements](requirements.md)
- [Pencil MCP 接入说明](docs/pencil-mcp-setup.md)

### 开发准备

- [架构文档](docs/architecture.md)
- [技术方案](docs/technical-design.md)
- [数据模型](docs/data-model.md)
- [数据库设计](docs/database-schema.md)
- [开发启动文档](docs/dev-start.md)
- [MySQL 初始化脚本](sql/mysql_init.sql)
- [开发规范](CONTRIBUTING.md)

## 设计资源

### 当前主设计稿

- [白色主主题设计稿](designs/paperchatagent-workbench.pen)

### 备选设计稿

- [AI 工作台版设计稿](designs/paperchatagent-workbench-ai-workbench.pen)
- [Claude Code 风格设计稿](designs/paperchatagent-workbench-claudecode.pen)

### 白色主主题预览

- [首页](images/light-main/home-wireframe.png)
- [登录页](images/light-main/login-wireframe.png)
- [注册页](images/light-main/register-wireframe.png)
- [知识库页](images/light-main/knowledge-wireframe.png)
- [智能体页](images/light-main/agents-wireframe.png)
- [后台任务页](images/light-main/tasks-wireframe.png)

### 备选主题预览

- `images/ai-workbench/`
- `images/claudecode/`

## 运行方式

### 前端本地运行

```bash
cd apps/frontend
pnpm install
pnpm dev
```

默认访问地址：

- `http://127.0.0.1:5173`

### 当前前端构建检查

```bash
cd apps/frontend
pnpm build
```

当前前端构建已通过。

### 前端目录位置

- `apps/frontend`

### 后端本地运行

```bash
cd apps/backend
uv sync
cp paperchat/config.example.yaml paperchat/config.yaml
uv run uvicorn paperchat.main:app --host 127.0.0.1 --port 8000 --reload
```

默认地址：

- API: `http://127.0.0.1:8000/api/v1`
- Swagger: `http://127.0.0.1:8000/swagger`

当前后端启动时会自动初始化数据库基础表，但研究工作流的中间结果目前仍主要保存在内存态 store 中。

## 目录结构

更新约定：

- 只要目录结构、模块职责或服务拆分发生变化，必须同步更新本节 tree
- 本节 tree 应与 `docs/architecture.md` 中的完整目录树保持一致

```text
PaperChatAgent/
├── apps/
│   ├── frontend/                          # Vue 3 工作台前端
│   │   ├── src/
│   │   │   ├── apis/                      # 前端 API client，按资源拆分
│   │   │   ├── components/                # 业务复用组件
│   │   │   ├── layouts/                   # 页面布局，如工作台主布局、登录布局
│   │   │   ├── mocks/                     # mock 数据
│   │   │   ├── pages/                     # 页面级视图
│   │   │   ├── router/                    # 路由配置
│   │   │   ├── stores/                    # Pinia 状态管理
│   │   │   ├── types/                     # 前端 DTO / 页面类型定义
│   │   │   └── utils/                     # 通用工具函数
│   │   ├── package.json                   # 前端依赖定义
│   │   ├── pnpm-lock.yaml                 # 前端锁文件
│   │   └── vite.config.ts                 # Vite 配置
│   ├── backend/                           # FastAPI 主服务（已实现基础 API 与研究工作流骨架）
│   │   └── paperchat/
│   │       ├── main.py                    # 后端应用入口
│   │       ├── settings.py                # 配置加载入口
│   │       ├── config.example.yaml        # 本地开发配置示例
│   │       ├── api/                       # HTTP / SSE 接口层
│   │       │   ├── responses/             # 统一响应对象
│   │       │   ├── errcode/               # 错误码定义
│   │       │   ├── router.py              # 顶层路由聚合
│   │       │   └── v1/                    # V1 业务接口
│   │       ├── auth/                      # JWT 认证与登录态
│   │       ├── middleware/                # CORS、Trace ID、审计等中间件
│   │       ├── core/                      # 运行时公共能力
│   │       ├── services/                  # 业务服务层
│   │       │   ├── chat/                  # 聊天服务
│   │       │   ├── workspace/             # 工作区服务
│   │       │   ├── knowledge/             # 知识库服务
│   │       │   ├── task/                  # 任务服务
│   │       │   ├── rag/                   # RAG 检索增强
│   │       │   ├── rewrite/               # 查询改写
│   │       │   └── storage/               # MinIO / 对象存储抽象
│   │       ├── database/                  # 持久化层
│   │       │   ├── models/                # ORM / SQLModel 模型
│   │       │   └── dao/                   # 数据访问对象
│   │       ├── workflows/                 # 完整研究工作流
│   │       │   ├── graph/                 # LangGraph 图定义
│   │       │   ├── nodes/                 # search/reading/analyse/writing/report 节点
│   │       │   └── agents/                # AutoGen 智能体定义
│   │       ├── tasks/                     # 后台任务入口与调度封装
│   │       ├── schemas/                   # Pydantic 请求/响应模型
│   │       └── providers/                 # LangChain / 模型供应商抽象
│   └── worker/                            # 独立后台执行器（当前仍为占位骨架）
│       └── paperchat_worker/
│           ├── main.py                    # worker 入口
│           ├── consumers/                 # 队列消费者
│           ├── jobs/                      # 具体任务实现
│           └── utils/                     # worker 公共工具
├── designs/                               # Pencil 设计稿
├── docs/                                  # 产品、架构、技术、数据库文档
├── images/                                # 页面导出预览图
├── sql/                                   # 初始化 SQL 与数据库脚本
├── CONTRIBUTING.md                        # 开发规范
├── README.md                              # 项目入口说明
├── requirements.md                        # 英文 PRD
└── 需求文档.md                             # 中文 PRD
```

## 分支与协作

当前仓库采用：

- `main`：稳定主线
- `develop`：开发主线

常规短期分支命名：

- `feature/*`
- `fix/*`
- `docs/*`
- `refactor/*`
- `chore/*`
- `release/*`
- `hotfix/*`

详细规则见：

- [CONTRIBUTING.md](CONTRIBUTING.md)

## 当前最建议的下一步

如果继续往下推进，推荐顺序是：

1. 把任务运行时从内存态迁到正式表结构
2. 为 worker 接入 Redis 队列消费，切断 API 进程内 `create_task` 执行
3. 接通 ChromaDB 与更完整的知识检索
4. 联调前端聊天页、任务页、智能体页真实接口
5. 接回 search 节点的人审代理与前端交互
6. 再补 docker compose 和一键本地开发环境
