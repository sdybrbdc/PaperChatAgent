# PaperChatAgent

Personal project workspace for PaperChatAgent.

## Project Docs

- [需求文档](需求文档.md)
- [Requirements](requirements.md)
- [Pencil MCP 接入说明](docs/pencil-mcp-setup.md)

## Development Prep

- [架构文档](docs/architecture.md)
- [技术方案](docs/technical-design.md)
- [数据模型](docs/data-model.md)
- [数据库设计](docs/database-schema.md)
- [开发启动文档](docs/dev-start.md)
- [MySQL 初始化脚本](sql/mysql_init.sql)

## Architecture Tree

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
│   │   │   ├── pages/                     # 页面级视图
│   │   │   ├── router/                    # 路由配置
│   │   │   ├── stores/                    # Pinia 状态管理
│   │   │   ├── types/                     # 前端 DTO / 页面类型定义
│   │   │   └── utils/                     # 通用工具函数
│   │   ├── package.json                   # 前端依赖定义
│   │   └── vite.config.ts                 # Vite 配置
│   ├── backend/                           # FastAPI 主服务
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
│   └── worker/                            # 独立后台执行器
│       └── paperchat_worker/
│           ├── main.py                    # worker 入口
│           ├── consumers/                 # 队列消费者
│           ├── jobs/                      # 具体任务实现
│           └── utils/                     # worker 公共工具
├── docs/                                  # 产品、架构、技术、数据库文档
├── designs/                               # Pencil 设计稿
├── images/                                # 页面导出预览图
├── sql/                                   # 初始化 SQL 与数据库脚本
├── README.md                              # 项目入口说明
├── 需求文档.md                             # 中文 PRD
└── requirements.md                        # 英文 PRD
```

## Design Workspace

- Pencil design file: [designs/paperchatagent-workbench.pen](designs/paperchatagent-workbench.pen)
