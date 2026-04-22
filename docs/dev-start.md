# PaperChatAgent 开发启动文档

## 1. 文档目标

本文档用于说明如何从当前仓库出发，搭建 PaperChatAgent 的首个可运行开发环境。

本文档只覆盖：

- 本地开发环境
- 本地测试环境
- 服务依赖准备
- 推荐命令与目录结构

本文档不覆盖：

- 正式生产部署
- 云资源编排
- CI/CD

## 2. 推荐仓库结构

建议在当前仓库中逐步形成如下结构：

```text
PaperChatAgent/
├── apps/
│   ├── frontend/
│   ├── backend/
│   └── worker/
├── docs/
├── designs/
├── images/
├── 需求文档.md
├── requirements.md
└── README.md
```

说明：

- `frontend`：Vue 3 工作台
- `backend`：FastAPI API 服务
- `worker`：异步研究任务执行器

## 3. 包管理与命令约定

### 3.1 前端

- 包管理：`pnpm`
- 路由：`vue-router`
- 状态管理：`pinia`
- 组件库：`element-plus`
- 原因：
  - 安装速度快
  - 更适合 Monorepo
  - 前端生态兼容良好
  - 方便快速搭建工作台类业务页面

### 3.2 后端

- 包管理与环境管理：`uv`
- 原因：
- 环境初始化快
- 适合现代 Python 项目启动
- 比 Poetry 更轻

### 3.3 工作流与聊天依赖

后端依赖层从一开始就明确以下两条主线：

- 聊天层：LangChain
- 工作流层：AutoGen + LangGraph

## 4. 本地依赖服务

V1 推荐准备以下依赖服务：

- MySQL
- Redis
- MinIO
- ChromaDB

## 5. 启动方式

### 5.1 推荐方式：Docker Compose

推荐使用 Docker Compose 启动本地依赖服务，因为：

- 环境一致性更好
- 新开发者更容易复现
- 与 README 和示例 YAML 更容易保持一致

### 5.2 兼容方式：本机直连

如果开发机已经常驻以下服务，也允许直接在 `config.yaml` 中配置本机地址：

- 本地 MySQL
- 本地 Redis
- 本地 MinIO
- 本地 Chroma

## 6. 配置文件

### 6.1 文件约定

- `apps/backend/paperchat/config.example.yaml`
- `apps/backend/paperchat/config.yaml`

### 6.2 使用方式

```bash
cp apps/backend/paperchat/config.example.yaml apps/backend/paperchat/config.yaml
```

然后填写：

- MySQL 地址
- Redis 地址
- MinIO 地址
- ChromaDB 地址
- 模型密钥与 base_url
- LangChain / AutoGen 所需模型路由配置

### 6.3 示例配置结构

```yaml
server:
  env: "dev"
  host: "127.0.0.1"
  port: 8000

mysql:
  endpoint: "mysql+pymysql://root:password@127.0.0.1:3306/paperchatagent"
  async_endpoint: "mysql+aiomysql://root:password@127.0.0.1:3306/paperchatagent"

redis:
  endpoint: "redis://127.0.0.1:6379"

storage:
  mode: "minio"
  minio:
    endpoint: "127.0.0.1:9000"
    access_key_id: "minioadmin"
    access_key_secret: "minioadmin"
    bucket_name: "paperchatagent"

vector_db:
  mode: "chroma"
  host: "127.0.0.1"
  port: 8001

multi_models:
  conversation_model:
    api_key: "your-key"
    base_url: "https://your-openai-compatible-endpoint/v1"
    model_name: "gpt-4o-mini"
  tool_call_model:
    api_key: "your-key"
    base_url: "https://your-openai-compatible-endpoint/v1"
    model_name: "gpt-4o-mini"
  reasoning_model:
    api_key: "your-key"
    base_url: "https://your-reasoning-endpoint/v1"
    model_name: "deepseek-reasoner"
  qwen_vl:
    api_key: "${DASHSCOPE_API_KEY}"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model_name: "qwen-vl-plus"
  embedding:
    api_key: "your-key"
    base_url: "https://your-embedding-endpoint/v1"
    model_name: "text-embedding-3-large"
  rerank:
    api_key: "your-key"
    base_url: "https://your-rerank-endpoint/v1"
    model_name: "rerank-model"
  text2image:
    api_key: "${DASHSCOPE_API_KEY}"
    base_url: "https://your-text2image-endpoint"
    model_name: "text2image-model"

workflow:
  engine: "langgraph"
  agents_runtime: "autogen"
  hitl_enabled: true
```

## 7. 首次启动路径

### 7.1 起依赖服务

优先方式：

```bash
docker compose up -d
```

### 7.2 配置 YAML

- 复制 `config.example.yaml`
- 填写数据库、Redis、MinIO、模型密钥

### 7.3 启动 backend

建议命令形态：

```bash
cd apps/backend
uv sync
uv run uvicorn paperchat.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7.4 启动 worker

建议命令形态：

```bash
cd apps/worker
uv sync
uv run python -m paperchat_worker.main
```

### 7.5 启动 frontend

建议命令形态：

```bash
cd apps/frontend
pnpm install
pnpm dev
```

前端默认依赖建议包括：

```bash
pnpm add vue-router pinia element-plus @element-plus/icons-vue axios
```

### 7.6 访问默认聊天页

默认访问：

- Frontend：`http://127.0.0.1:5173`
- Backend：`http://127.0.0.1:8000`

登录成功后应进入默认聊天页。

## 8. README 需要同步的信息

README 至少应补充以下索引：

- 开发准备
- 架构文档
- 技术方案
- 数据模型
- 启动说明

## 9. 开发第一阶段建议顺序

建议按以下顺序开始实现：

1. 初始化 Monorepo 目录结构
2. 搭建 FastAPI 基础服务和认证
3. 搭建 LangChain 模型管理与聊天服务
4. 搭建 Vue 工作台壳与默认聊天页
5. 接入 MySQL / Redis / MinIO / Chroma
6. 搭建工作区与会话模型
7. 搭建任务创建与 SSE 进度流
8. 接入完整 Paper-Agent 风格工作流
9. 打通知识上传、arXiv 导入与报告产物回流

## 10. 验收标准

当以下条件满足时，可认为开发环境准备完成：

- 一条命令或一组明确命令可以启动本地依赖服务
- backend 可启动
- worker 可启动
- frontend 可启动
- 用户登录后能进入默认聊天页
