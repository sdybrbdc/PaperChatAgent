# PaperChatAgent 开发启动文档

## 1. 文档目标

本文档用于说明 PaperChatAgent V1 的本地开发准备、配置方式、启动命令和当前实现状态。

说明：

- 新文档以“聊天主链路 + 模块化能力”作为目标口径
- 当前仓库仍有部分旧命名和过渡结构
- 本文档会同时标注目标模块和当前实现现状

## 2. 本地环境准备

建议准备：

- Node.js 18+
- pnpm
- Python 3.11+
- uv
- MySQL 8+
- MinIO
- ChromaDB

## 3. 配置文件

后端配置建议使用：

- `apps/backend/paperchat/config.example.yaml`
- `apps/backend/paperchat/config.yaml`

建议配置段包括：

- `server`
- `mysql`
- `storage`
- `vector_db`
- `model_routes`
- `mcp`
- `skills`

### 3.1 配置示例

```yaml
server:
  host: "127.0.0.1"
  port: 8000

mysql:
  endpoint: "mysql+pymysql://root:password@127.0.0.1:3306/paperchatagent"
  async_endpoint: "mysql+aiomysql://root:password@127.0.0.1:3306/paperchatagent"

storage:
  mode: "minio"
  minio:
    endpoint: "127.0.0.1:9000"
    access_key_id: "minioadmin"
    access_key_secret: "minioadmin"
    bucket_name: "paperchatagent"

vector_db:
  provider: "chromadb"
  endpoint: "http://127.0.0.1:8001"

model_routes:
  conversation:
    provider: "openai_compatible"
    base_url: "https://your-openai-compatible-endpoint/v1"
    api_key: "your-key"
    model_name: "gpt-4o-mini"
  tool_call:
    provider: "openai_compatible"
    base_url: "https://your-openai-compatible-endpoint/v1"
    api_key: "your-key"
    model_name: "gpt-4o-mini"
  reasoning:
    provider: "openai_compatible"
    base_url: "https://your-reasoning-endpoint/v1"
    api_key: "your-key"
    model_name: "deepseek-reasoner"
  embedding:
    provider: "openai_compatible"
    base_url: "https://your-embedding-endpoint/v1"
    api_key: "your-key"
    model_name: "text-embedding-3-large"
  rerank:
    provider: "http"
    base_url: "https://your-rerank-endpoint"
    api_key: "your-key"
    model_name: "rerank-model"

mcp:
  enabled: true
  servers: []

skills:
  enabled: true
  items: []
```

## 4. 启动方式

### 4.1 启动前端

```bash
cd apps/frontend
pnpm install
pnpm dev
```

默认访问：

- `http://127.0.0.1:5173`

### 4.2 启动后端

```bash
cd apps/backend
uv sync
cp paperchat/config.example.yaml paperchat/config.yaml
uv run uvicorn paperchat.main:app --host 127.0.0.1 --port 8000 --reload
```

默认访问：

- API：`http://127.0.0.1:8000/api/v1`
- Swagger：`http://127.0.0.1:8000/swagger`

### 4.3 启动依赖服务

本地至少需要可用的：

- MySQL
- MinIO
- ChromaDB

项目当前未提供统一的依赖编排脚本时，可使用你自己的本地常驻服务或 Compose 环境。

## 5. 模块级开发说明

### 5.1 Chat

当前是最先联调的模块。

开发重点：

- 会话列表
- 消息列表
- SSE 聊天流
- 会话级长期摘要
- 自主检索 / 自主工具调用的演进空间

### 5.2 Knowledge

目标职责：

- 知识库创建
- 文件上传与导入
- 文档解析
- 切片与向量化
- 为聊天检索提供来源

当前状态：

- 已有基础资料上传和导入接口
- 知识库主表与向量检索闭环仍在后续范围

### 5.3 Agents

目标职责：

- 注册与展示内置工作流
- 为聊天和后台任务提供可调用工作流能力

当前状态：

- 已有默认工作流与节点说明接口
- 当前内置多节点研究工作流骨架

### 5.4 Models

目标职责：

- 统一模型配置
- 统一逻辑槽位路由

当前状态：

- provider 抽象已存在
- 独立模型模块页面与完整配置接口仍待补齐

### 5.5 MCP / Skills

目标职责：

- 管理配置列表
- 导入本地项
- 新增自定义项

当前状态：

- 前端和后端还未完整实现为独立模块

### 5.6 Tasks

目标职责：

- 展示研究任务
- 展示工作流运行与节点进度
- 返回结果摘要

当前状态：

- 已有任务创建、任务列表、任务详情、任务事件流
- 当前页面定位延续“展示智能体进度”的产品认知
- 当前执行方式为进程内异步任务
- 当前恢复机制包含自动重试、节点暂停、从失败节点续跑、备用模型切换、checkpoint 持久化

### 5.7 Dashboard

目标职责：

- 展示模型调用、输入输出量、任务分布等指标

当前状态：

- 仍为待扩展模块

## 6. 当前实现过渡说明

当前代码库中仍保留一些历史命名：

- `WorkbenchLayout`
- `paperchat_workspaces`
- `workspace_id` 相关字段

这些名称不再代表新的产品主叙事，只是当前代码兼容结构。

同样地：

- 当前版本不再保留独立 worker 骨架
- 任务逻辑统一运行在后端进程内

## 7. 推荐开发顺序

建议按以下顺序推进：

1. 完成认证与会话恢复
2. 打通聊天主链路
3. 补齐知识库创建、文件上传、解析与索引
4. 补齐模型路由配置
5. 打通智能体工作流与任务进度
6. 增加 MCP 模块与 Skills 模块
7. 增加数据看板
8. 逐步清理旧的 `workspace / workbench` 命名

## 8. 验收标准

当以下条件满足时，可认为本地开发环境可用：

- 前端可以启动
- 后端可以启动
- 用户登录后可进入聊天页
- 聊天接口可工作
- 任务接口可工作
- 至少具备知识资料上传或导入的基础能力
