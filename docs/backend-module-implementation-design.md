# PaperChatAgent 后端模块化实现设计

## 1. 文档目标

本文档给出 PaperChatAgent V1 后端的完整落地方案，覆盖：

- 数据库表设计
- API 契约
- 目录与文件路径
- RAG、MCP、Skills、模型路由、后台任务、数据看板的具体实现方式
- Chat / Agents 与这些模块之间的能力交换方式

本文档基于当前仓库现状设计：

- 已有 `auth / conversations / agents` API。
- 已有 `paperchat_users / paperchat_conversations / paperchat_messages / paperchat_agent_workflows / paperchat_research_tasks / paperchat_workflow_runs / paperchat_workflow_node_runs / paperchat_task_artifacts` 等基础表。
- 当前代码使用 `conversation_id` 表达聊天会话，因此后续新增表统一使用 `conversation_id`，不再新引入 `session_id` 混名。

## 2. 总体原则

### 2.1 模块边界

后端分为两类模块：

1. 产品业务模块：面向前端页面和用户对象。
2. 能力实现模块：面向 Chat、Agents、Tasks 的内部调用。

对应关系如下：

| 产品模块 | API 前缀 | 业务服务 | 能力实现 |
|---|---|---|---|
| 知识库 | `/api/v1/knowledge` | `services/knowledge` | `services/rag` |
| MCP 服务 | `/api/v1/mcp` | `services/mcp` | `services/mcp` |
| Skills | `/api/v1/skills` | `services/skills` | `services/skills` |
| 模型 | `/api/v1/models` | `services/model_router` | `services/model_router` |
| 后台任务 | `/api/v1/tasks` | `services/tasks` | `services/tasks` |
| 数据看板 | `/api/v1/dashboard` | `services/dashboard` | `services/dashboard` |
| 能力交换 | 内部优先，可选 `/api/v1/capabilities` | `services/capabilities` | 汇总 RAG / MCP / Skills / Agents |

### 2.2 调用方向

禁止 Chat / Agents 直接 import 具体能力实现，例如：

- 不建议 `chat.service` 直接 import `skills.executor`
- 不建议 `agents.service` 直接 import `mcp.client`
- 不建议工作流节点直接读模型配置表

推荐统一通过：

```text
Chat / Agents / Tasks
  -> services/capabilities
  -> services/rag / services/mcp / services/skills / services/model_router
  -> database / storage / vector store
```

### 2.3 数据存储边界

| 数据类型 | 存储位置 |
|---|---|
| 用户、配置、状态、索引元数据 | MySQL |
| 原始 PDF、解析文本、任务产物大文件 | MinIO 或本地对象存储 |
| 向量 | ChromaDB 或后续可替换 Vector Store |
| SSE 实时事件 | 内存队列 + MySQL 事件表回放 |
| Dashboard 指标 | 调用日志表 + 可选快照表 |

MySQL 不直接存二进制文件和向量，只保存 object key、collection、vector id、定位元数据。

## 3. 推荐目录结构

```text
apps/backend/paperchat/
├── api/
│   └── v1/
│       ├── auth.py
│       ├── conversations.py
│       ├── agents.py
│       ├── knowledge.py
│       ├── mcp.py
│       ├── skills.py
│       ├── models.py
│       ├── tasks.py
│       ├── dashboard.py
│       ├── capabilities.py        # 可选，仅用于配置页/调试页读取可调用能力
│       └── router.py
│
├── schemas/
│   ├── common.py
│   ├── knowledge.py
│   ├── rag.py
│   ├── mcp.py
│   ├── skills.py
│   ├── models.py
│   ├── tasks.py
│   ├── dashboard.py
│   └── capabilities.py
│
├── services/
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   └── conversation_binding.py
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── service.py             # 对外 retrieve / index_file
│   │   ├── pipeline.py            # 解析、切片、embedding、入库编排
│   │   ├── parser.py              # PDF / text parser 抽象
│   │   ├── chunker.py
│   │   ├── embedding.py
│   │   ├── retriever.py
│   │   ├── vector_store.py
│   │   └── citation.py
│   │
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── service.py             # 配置 CRUD
│   │   ├── registry.py            # MCP 服务和工具注册表
│   │   ├── client.py              # MCP client 生命周期
│   │   ├── tool_adapter.py        # MCP tool -> Capability
│   │   └── healthcheck.py
│   │
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── service.py             # Skill 配置 CRUD
│   │   ├── registry.py
│   │   ├── loader.py              # 从目录 / repo / builtin 加载
│   │   ├── executor.py
│   │   ├── validator.py
│   │   └── builtin/
│   │       └── literature_search.py
│   │
│   ├── model_router/
│   │   ├── __init__.py
│   │   ├── service.py             # 配置 CRUD + 测试调用
│   │   ├── router.py              # slot -> provider/model
│   │   ├── slots.py
│   │   ├── usage_recorder.py
│   │   └── providers/
│   │       ├── base.py
│   │       ├── openai.py
│   │       ├── deepseek.py
│   │       └── local.py
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── runtime.py             # asyncio 后台任务运行时
│   │   ├── event_bus.py           # SSE 事件发布和订阅
│   │   └── node_runner.py
│   │
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── service.py
│   │   ├── metrics.py
│   │   └── collectors.py
│   │
│   └── capabilities/
│       ├── __init__.py
│       ├── contracts.py           # Capability / ToolCall / ToolResult
│       ├── registry.py
│       └── executor.py
│
├── database/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── tables.py              # 过渡期保留已有表
│   │   ├── knowledge.py
│   │   ├── mcp.py
│   │   ├── skills.py
│   │   ├── models.py
│   │   ├── tasks.py
│   │   └── metrics.py
│   └── dao/
│       ├── __init__.py
│       ├── knowledge.py
│       ├── mcp.py
│       ├── skills.py
│       ├── models.py
│       ├── tasks.py
│       └── metrics.py
```

说明：

- 当前 `database/models/tables.py` 已经承载很多表。短期可以继续追加，等模块稳定后再拆到 `database/models/*.py`。
- 对外 API 只写薄封装，业务逻辑放在 `services/*/service.py`。
- RAG 是能力实现模块，不直接等同知识库页面。

## 4. 数据库设计

### 4.1 已有表继续沿用

| 表名 | 用途 | 处理方式 |
|---|---|---|
| `paperchat_users` | 用户 | 沿用 |
| `paperchat_user_sessions` | 登录态 | 沿用 |
| `paperchat_conversations` | 聊天会话 | 沿用 |
| `paperchat_messages` | 消息 | 沿用，短期继续用 `citations_json` |
| `paperchat_conversation_guidance_snapshots` | 聊天引导状态 | 沿用 |
| `paperchat_conversation_realtime_events` | 聊天实时事件 | 沿用 |
| `paperchat_conversation_memories` | 会话记忆 | 沿用 |
| `paperchat_user_memories` | 用户记忆 | 沿用 |
| `paperchat_agent_workflows` | Agent 工作流定义 | 沿用 |
| `paperchat_agent_node_config_overrides` | 节点配置覆盖 | 沿用 |
| `paperchat_research_tasks` | 研究任务 | 沿用，可补充 payload 字段 |
| `paperchat_workflow_runs` | 工作流运行 | 沿用 |
| `paperchat_workflow_node_runs` | 节点运行 | 沿用 |
| `paperchat_task_artifacts` | 任务产物 | 沿用 |

### 4.2 新增表总览

| 分组 | 表名 | 说明 |
|---|---|---|
| Knowledge | `paperchat_knowledge_bases` | 知识库主表 |
| Knowledge | `paperchat_knowledge_files` | 知识文件元数据 |
| Knowledge | `paperchat_knowledge_chunks` | RAG 文本切片和向量定位 |
| Knowledge | `paperchat_conversation_knowledge_bindings` | 会话与知识库绑定 |
| RAG | `paperchat_rag_index_jobs` | 文件解析/切片/索引任务 |
| RAG | `paperchat_rag_retrieval_logs` | 检索记录，用于引用和看板 |
| Citation | `paperchat_citation_evidences` | 规范化引用证据，可替代 `citations_json` |
| MCP | `paperchat_mcp_servers` | MCP 服务配置 |
| MCP | `paperchat_mcp_tools` | MCP 工具快照 |
| Skills | `paperchat_skill_configs` | Skill 配置 |
| Skills | `paperchat_skill_versions` | Skill manifest/version 快照 |
| Models | `paperchat_model_providers` | 模型供应商配置 |
| Models | `paperchat_model_route_configs` | 模型槽位路由 |
| Logs | `paperchat_model_invocation_logs` | 模型调用日志 |
| Logs | `paperchat_tool_invocation_logs` | RAG/MCP/Skill/Agent 工具调用日志 |
| Tasks | `paperchat_task_events` | 任务事件流持久化 |
| Dashboard | `paperchat_dashboard_metric_snapshots` | 看板指标快照 |

### 4.3 Knowledge / RAG 表

#### `paperchat_knowledge_bases`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_knowledge_bases` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `file_count` INT NOT NULL DEFAULT 0,
  `indexed_file_count` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_knowledge_bases_user_id` (`user_id`),
  KEY `idx_paperchat_knowledge_bases_status` (`status`),
  CONSTRAINT `fk_paperchat_knowledge_bases_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### `paperchat_knowledge_files`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_knowledge_files` (
  `id` VARCHAR(36) NOT NULL,
  `knowledge_base_id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `source_type` VARCHAR(32) NOT NULL DEFAULT 'upload',
  `title` VARCHAR(512) NOT NULL,
  `filename` VARCHAR(512) NOT NULL DEFAULT '',
  `mime_type` VARCHAR(128) NOT NULL DEFAULT '',
  `source_url` VARCHAR(1024) NOT NULL DEFAULT '',
  `object_key` VARCHAR(512) NOT NULL DEFAULT '',
  `parsed_text_object_key` VARCHAR(512) NOT NULL DEFAULT '',
  `parser_status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `index_status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `chunk_count` INT NOT NULL DEFAULT 0,
  `metadata_json` JSON NOT NULL,
  `error_text` TEXT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_knowledge_files_base_id` (`knowledge_base_id`),
  KEY `idx_paperchat_knowledge_files_user_id` (`user_id`),
  KEY `idx_paperchat_knowledge_files_parser_status` (`parser_status`),
  KEY `idx_paperchat_knowledge_files_index_status` (`index_status`),
  CONSTRAINT `fk_paperchat_knowledge_files_base_id`
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `paperchat_knowledge_bases` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_knowledge_files_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### `paperchat_knowledge_chunks`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_knowledge_chunks` (
  `id` VARCHAR(36) NOT NULL,
  `knowledge_base_id` VARCHAR(36) NOT NULL,
  `knowledge_file_id` VARCHAR(36) NOT NULL,
  `chunk_index` INT NOT NULL,
  `content` LONGTEXT NOT NULL,
  `content_hash` VARCHAR(64) NOT NULL,
  `page_no` INT DEFAULT NULL,
  `section_title` VARCHAR(255) NOT NULL DEFAULT '',
  `vector_collection` VARCHAR(255) NOT NULL DEFAULT '',
  `vector_doc_id` VARCHAR(255) NOT NULL DEFAULT '',
  `token_count` INT NOT NULL DEFAULT 0,
  `locator_json` JSON NOT NULL,
  `metadata_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_knowledge_chunk_file_index` (`knowledge_file_id`, `chunk_index`),
  KEY `idx_paperchat_knowledge_chunks_base_id` (`knowledge_base_id`),
  KEY `idx_paperchat_knowledge_chunks_file_id` (`knowledge_file_id`),
  KEY `idx_paperchat_knowledge_chunks_vector_doc_id` (`vector_doc_id`),
  CONSTRAINT `fk_paperchat_knowledge_chunks_base_id`
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `paperchat_knowledge_bases` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_knowledge_chunks_file_id`
    FOREIGN KEY (`knowledge_file_id`) REFERENCES `paperchat_knowledge_files` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### `paperchat_conversation_knowledge_bindings`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_conversation_knowledge_bindings` (
  `id` VARCHAR(36) NOT NULL,
  `conversation_id` VARCHAR(36) NOT NULL,
  `knowledge_base_id` VARCHAR(36) NOT NULL,
  `binding_type` VARCHAR(32) NOT NULL DEFAULT 'manual',
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_conversation_knowledge_binding` (`conversation_id`, `knowledge_base_id`),
  KEY `idx_paperchat_ckb_base_id` (`knowledge_base_id`),
  CONSTRAINT `fk_paperchat_ckb_conversation_id`
    FOREIGN KEY (`conversation_id`) REFERENCES `paperchat_conversations` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_ckb_base_id`
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `paperchat_knowledge_bases` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### `paperchat_rag_index_jobs`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_rag_index_jobs` (
  `id` VARCHAR(36) NOT NULL,
  `knowledge_file_id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'pending',
  `stage` VARCHAR(32) NOT NULL DEFAULT 'queued',
  `progress` INT NOT NULL DEFAULT 0,
  `parser_name` VARCHAR(128) NOT NULL DEFAULT '',
  `embedding_route_key` VARCHAR(64) NOT NULL DEFAULT 'embedding',
  `error_text` TEXT NOT NULL,
  `metadata_json` JSON NOT NULL,
  `started_at` DATETIME DEFAULT NULL,
  `completed_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_rag_index_jobs_file_id` (`knowledge_file_id`),
  KEY `idx_paperchat_rag_index_jobs_user_id` (`user_id`),
  KEY `idx_paperchat_rag_index_jobs_status` (`status`),
  CONSTRAINT `fk_paperchat_rag_index_jobs_file_id`
    FOREIGN KEY (`knowledge_file_id`) REFERENCES `paperchat_knowledge_files` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_rag_index_jobs_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### `paperchat_rag_retrieval_logs`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_rag_retrieval_logs` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `conversation_id` VARCHAR(36) DEFAULT NULL,
  `message_id` VARCHAR(36) DEFAULT NULL,
  `query_text` TEXT NOT NULL,
  `knowledge_base_ids_json` JSON NOT NULL,
  `top_k` INT NOT NULL DEFAULT 8,
  `result_count` INT NOT NULL DEFAULT 0,
  `latency_ms` INT NOT NULL DEFAULT 0,
  `results_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_rag_logs_user_id` (`user_id`),
  KEY `idx_paperchat_rag_logs_conversation_id` (`conversation_id`),
  KEY `idx_paperchat_rag_logs_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### `paperchat_citation_evidences`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_citation_evidences` (
  `id` VARCHAR(36) NOT NULL,
  `message_id` VARCHAR(36) NOT NULL,
  `knowledge_file_id` VARCHAR(36) DEFAULT NULL,
  `knowledge_chunk_id` VARCHAR(36) DEFAULT NULL,
  `retrieval_log_id` VARCHAR(36) DEFAULT NULL,
  `label` VARCHAR(255) NOT NULL,
  `snippet` TEXT NOT NULL,
  `score` FLOAT NOT NULL DEFAULT 0,
  `locator_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_citations_message_id` (`message_id`),
  KEY `idx_paperchat_citations_file_id` (`knowledge_file_id`),
  KEY `idx_paperchat_citations_chunk_id` (`knowledge_chunk_id`),
  CONSTRAINT `fk_paperchat_citations_message_id`
    FOREIGN KEY (`message_id`) REFERENCES `paperchat_messages` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 4.4 MCP 表

#### `paperchat_mcp_servers`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_mcp_servers` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `transport_type` VARCHAR(32) NOT NULL DEFAULT 'stdio',
  `command` VARCHAR(512) NOT NULL DEFAULT '',
  `args_json` JSON NOT NULL,
  `endpoint_url` VARCHAR(1024) NOT NULL DEFAULT '',
  `headers_json` JSON NOT NULL,
  `env_json` JSON NOT NULL,
  `secret_config_json` JSON NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'disabled',
  `last_health_status` VARCHAR(32) NOT NULL DEFAULT 'unknown',
  `last_checked_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_mcp_servers_user_id` (`user_id`),
  KEY `idx_paperchat_mcp_servers_status` (`status`),
  CONSTRAINT `fk_paperchat_mcp_servers_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### `paperchat_mcp_tools`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_mcp_tools` (
  `id` VARCHAR(36) NOT NULL,
  `server_id` VARCHAR(36) NOT NULL,
  `tool_name` VARCHAR(255) NOT NULL,
  `display_name` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `input_schema_json` JSON NOT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `last_seen_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_mcp_tool_server_name` (`server_id`, `tool_name`),
  KEY `idx_paperchat_mcp_tools_server_id` (`server_id`),
  CONSTRAINT `fk_paperchat_mcp_tools_server_id`
    FOREIGN KEY (`server_id`) REFERENCES `paperchat_mcp_servers` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 4.5 Skills 表

#### `paperchat_skill_configs`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_skill_configs` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT NOT NULL,
  `source_type` VARCHAR(32) NOT NULL DEFAULT 'local',
  `source_uri` VARCHAR(1024) NOT NULL DEFAULT '',
  `entrypoint` VARCHAR(512) NOT NULL DEFAULT '',
  `status` VARCHAR(32) NOT NULL DEFAULT 'disabled',
  `manifest_json` JSON NOT NULL,
  `input_schema_json` JSON NOT NULL,
  `output_schema_json` JSON NOT NULL,
  `metadata_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_skill_configs_user_id` (`user_id`),
  KEY `idx_paperchat_skill_configs_status` (`status`),
  CONSTRAINT `fk_paperchat_skill_configs_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### `paperchat_skill_versions`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_skill_versions` (
  `id` VARCHAR(36) NOT NULL,
  `skill_id` VARCHAR(36) NOT NULL,
  `version` VARCHAR(64) NOT NULL,
  `manifest_json` JSON NOT NULL,
  `checksum` VARCHAR(128) NOT NULL DEFAULT '',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_skill_version` (`skill_id`, `version`),
  CONSTRAINT `fk_paperchat_skill_versions_skill_id`
    FOREIGN KEY (`skill_id`) REFERENCES `paperchat_skill_configs` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 4.6 Models 表

#### `paperchat_model_providers`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_model_providers` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `provider_key` VARCHAR(128) NOT NULL,
  `display_name` VARCHAR(255) NOT NULL,
  `base_url` VARCHAR(1024) NOT NULL DEFAULT '',
  `api_key_secret_ref` VARCHAR(512) NOT NULL DEFAULT '',
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `metadata_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_model_provider_user_key` (`user_id`, `provider_key`),
  KEY `idx_paperchat_model_providers_user_id` (`user_id`),
  CONSTRAINT `fk_paperchat_model_providers_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### `paperchat_model_route_configs`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_model_route_configs` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `route_key` VARCHAR(64) NOT NULL,
  `provider_id` VARCHAR(36) NOT NULL,
  `model_name` VARCHAR(255) NOT NULL,
  `temperature` FLOAT DEFAULT NULL,
  `max_tokens` INT DEFAULT NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `config_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paperchat_model_route_user_key` (`user_id`, `route_key`),
  KEY `idx_paperchat_model_routes_user_id` (`user_id`),
  KEY `idx_paperchat_model_routes_provider_id` (`provider_id`),
  CONSTRAINT `fk_paperchat_model_routes_user_id`
    FOREIGN KEY (`user_id`) REFERENCES `paperchat_users` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_paperchat_model_routes_provider_id`
    FOREIGN KEY (`provider_id`) REFERENCES `paperchat_model_providers` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

`route_key` 建议固定：

| route_key | 用途 |
|---|---|
| `conversation` | 普通聊天 |
| `reasoning` | 深度推理、研究规划 |
| `tool_call` | 工具调用决策 |
| `embedding` | 向量化 |
| `rerank` | 检索重排 |
| `summary` | 摘要、记忆压缩 |

### 4.7 Logs / Dashboard 表

#### `paperchat_model_invocation_logs`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_model_invocation_logs` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `conversation_id` VARCHAR(36) DEFAULT NULL,
  `task_id` VARCHAR(36) DEFAULT NULL,
  `workflow_run_id` VARCHAR(36) DEFAULT NULL,
  `route_key` VARCHAR(64) NOT NULL,
  `provider_key` VARCHAR(128) NOT NULL,
  `model_name` VARCHAR(255) NOT NULL,
  `input_tokens` INT NOT NULL DEFAULT 0,
  `output_tokens` INT NOT NULL DEFAULT 0,
  `latency_ms` INT NOT NULL DEFAULT 0,
  `status` VARCHAR(32) NOT NULL DEFAULT 'success',
  `error_code` VARCHAR(128) NOT NULL DEFAULT '',
  `metadata_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_model_logs_user_id` (`user_id`),
  KEY `idx_paperchat_model_logs_route_key` (`route_key`),
  KEY `idx_paperchat_model_logs_created_at` (`created_at`),
  KEY `idx_paperchat_model_logs_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### `paperchat_tool_invocation_logs`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_tool_invocation_logs` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `conversation_id` VARCHAR(36) DEFAULT NULL,
  `task_id` VARCHAR(36) DEFAULT NULL,
  `capability_id` VARCHAR(255) NOT NULL,
  `capability_type` VARCHAR(32) NOT NULL,
  `input_json` JSON NOT NULL,
  `output_json` JSON NOT NULL,
  `latency_ms` INT NOT NULL DEFAULT 0,
  `status` VARCHAR(32) NOT NULL DEFAULT 'success',
  `error_text` TEXT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_tool_logs_user_id` (`user_id`),
  KEY `idx_paperchat_tool_logs_capability_type` (`capability_type`),
  KEY `idx_paperchat_tool_logs_created_at` (`created_at`),
  KEY `idx_paperchat_tool_logs_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### `paperchat_task_events`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_task_events` (
  `id` VARCHAR(36) NOT NULL,
  `task_id` VARCHAR(36) NOT NULL,
  `workflow_run_id` VARCHAR(36) DEFAULT NULL,
  `node_id` VARCHAR(64) NOT NULL DEFAULT '',
  `event_type` VARCHAR(64) NOT NULL,
  `payload_json` JSON NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_task_events_task_id` (`task_id`),
  KEY `idx_paperchat_task_events_created_at` (`created_at`),
  CONSTRAINT `fk_paperchat_task_events_task_id`
    FOREIGN KEY (`task_id`) REFERENCES `paperchat_research_tasks` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### `paperchat_dashboard_metric_snapshots`

```sql
CREATE TABLE IF NOT EXISTS `paperchat_dashboard_metric_snapshots` (
  `id` VARCHAR(36) NOT NULL,
  `user_id` VARCHAR(36) NOT NULL,
  `metric_key` VARCHAR(128) NOT NULL,
  `metric_value` FLOAT NOT NULL DEFAULT 0,
  `dimension_json` JSON NOT NULL,
  `recorded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_paperchat_metric_snapshots_user_key` (`user_id`, `metric_key`),
  KEY `idx_paperchat_metric_snapshots_recorded_at` (`recorded_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 5. API 契约

所有非 SSE 接口沿用当前响应格式：

```json
{
  "code": "OK",
  "message": "success",
  "data": {},
  "request_id": "trace-id"
}
```

### 5.1 Knowledge API

#### `GET /api/v1/knowledge/bases`

返回当前用户知识库列表。

查询参数：

- `status`: 可选，默认 `active`
- `keyword`: 可选

返回：

```json
{
  "items": [
    {
      "id": "kb-id",
      "name": "Diffusion Papers",
      "description": "扩散模型论文资料",
      "status": "active",
      "file_count": 12,
      "indexed_file_count": 9,
      "created_at": "2026-04-27T10:00:00Z",
      "updated_at": "2026-04-27T10:00:00Z"
    }
  ]
}
```

#### `POST /api/v1/knowledge/bases`

请求：

```json
{
  "name": "Diffusion Papers",
  "description": "扩散模型论文资料"
}
```

返回 `KnowledgeBaseDTO`。

#### `GET /api/v1/knowledge/bases/{base_id}`

返回知识库详情，包含文件统计和最近文件。

#### `PATCH /api/v1/knowledge/bases/{base_id}`

修改名称、描述、状态。

#### `GET /api/v1/knowledge/bases/{base_id}/files`

返回知识库文件列表。

#### `POST /api/v1/knowledge/bases/{base_id}/files/upload`

`multipart/form-data` 上传文件。后端流程：

1. 保存文件到 Storage。
2. 创建 `paperchat_knowledge_files`。
3. 创建 `paperchat_rag_index_jobs`。
4. 将索引任务交给 `tasks.runtime` 或轻量后台队列。
5. 返回文件 DTO 和 index job id。

#### `POST /api/v1/knowledge/import/arxiv`

请求：

```json
{
  "knowledge_base_id": "kb-id",
  "arxiv_id": "2401.00001"
}
```

返回 `KnowledgeFileDTO`。

#### `POST /api/v1/knowledge/conversation-bindings`

请求：

```json
{
  "conversation_id": "conversation-id",
  "knowledge_base_id": "kb-id",
  "binding_type": "manual"
}
```

返回绑定对象。

#### `GET /api/v1/knowledge/conversations/{conversation_id}/bindings`

返回某个会话绑定的知识库列表。

### 5.2 MCP API

#### `GET /api/v1/mcp/services`

返回 MCP 服务列表。

#### `POST /api/v1/mcp/services`

请求：

```json
{
  "name": "Local Filesystem",
  "description": "本地文件检索工具",
  "transport_type": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
  "env": {},
  "status": "enabled"
}
```

说明：

- `env` 中的敏感值进入 `secret_config_json` 或外部 secret store。
- 返回时不回显明文 secret。

#### `GET /api/v1/mcp/services/{service_id}`

返回单个服务配置和工具快照。

#### `PATCH /api/v1/mcp/services/{service_id}`

更新服务配置。

#### `POST /api/v1/mcp/services/{service_id}/test`

测试连接并刷新 `last_health_status`。

#### `POST /api/v1/mcp/services/{service_id}/refresh-tools`

连接 MCP 服务，读取 tools，写入 `paperchat_mcp_tools`。

#### `GET /api/v1/mcp/tools`

返回所有启用 MCP 服务下的可用工具。

### 5.3 Skills API

#### `GET /api/v1/skills`

返回 Skill 列表。

#### `POST /api/v1/skills`

请求：

```json
{
  "name": "Literature Search",
  "description": "文献检索技能",
  "source_type": "local",
  "source_uri": "/Users/sdybdc/.codex/skills/literature-search",
  "entrypoint": "skill.py:run",
  "status": "enabled"
}
```

#### `POST /api/v1/skills/import`

从本地目录或 repo 导入 Skill manifest。

#### `GET /api/v1/skills/{skill_id}`

返回 Skill 配置、schema、版本。

#### `PATCH /api/v1/skills/{skill_id}`

更新启停、描述、entrypoint 等。

#### `POST /api/v1/skills/{skill_id}/test`

请求：

```json
{
  "input": {
    "query": "RAG evaluation survey"
  }
}
```

返回 Skill 执行结果和校验信息。

### 5.4 Models API

#### `GET /api/v1/models/providers`

返回模型供应商列表。

#### `POST /api/v1/models/providers`

创建供应商配置。

#### `PATCH /api/v1/models/providers/{provider_id}`

更新供应商配置。

#### `GET /api/v1/models/routes`

返回当前用户模型槽位配置。

#### `PUT /api/v1/models/routes/{route_key}`

请求：

```json
{
  "provider_id": "provider-id",
  "model_name": "gpt-4.1",
  "temperature": 0.2,
  "max_tokens": 4096,
  "config": {}
}
```

#### `POST /api/v1/models/test`

请求：

```json
{
  "route_key": "conversation",
  "prompt": "请用一句话介绍 PaperChatAgent"
}
```

返回测试输出、耗时、token 统计，并写入 `paperchat_model_invocation_logs`。

### 5.5 Tasks API

当前 Agents API 已有 `/agents/workflows/{workflow_id}/runs`。建议新增通用任务入口，保持后台任务页独立。

#### `GET /api/v1/tasks`

查询当前用户任务列表。

查询参数：

- `status`: 可选
- `conversation_id`: 可选
- `limit`: 默认 50

#### `POST /api/v1/tasks`

请求：

```json
{
  "conversation_id": "conversation-id",
  "workflow_id": "research-orchestrator",
  "title": "扩散模型可控生成调研",
  "payload": {
    "topic": "controllable diffusion generation",
    "max_papers": 8,
    "knowledge_base_ids": ["kb-id"]
  }
}
```

返回 `ResearchTaskDTO`。

#### `GET /api/v1/tasks/{task_id}`

返回任务详情、workflow run、node runs、artifacts。

#### `GET /api/v1/tasks/{task_id}/events`

SSE 事件：

- `task.created`
- `task.started`
- `task.progress`
- `node.started`
- `node.progress`
- `node.completed`
- `artifact.created`
- `task.completed`
- `task.failed`
- `ping`

#### `POST /api/v1/tasks/{task_id}/cancel`

取消任务。

### 5.6 Dashboard API

#### `GET /api/v1/dashboard/overview`

返回：

```json
{
  "model_call_count": 120,
  "input_tokens": 520000,
  "output_tokens": 130000,
  "tool_call_count": 37,
  "running_task_count": 2,
  "failed_task_count": 1
}
```

#### `GET /api/v1/dashboard/model-usage`

查询参数：

- `from`
- `to`
- `group_by`: `hour / day / route_key / provider`

#### `GET /api/v1/dashboard/task-distribution`

返回任务状态分布、平均耗时。

#### `GET /api/v1/dashboard/tool-usage`

返回 RAG / MCP / Skills 调用次数、失败率、平均耗时。

### 5.7 Capabilities API

Capabilities API 可以先作为内部服务，不一定立刻暴露给前端。若智能体配置页需要展示“可选执行器”，再开放只读接口。

#### `GET /api/v1/capabilities`

查询参数：

- `types`: `rag,mcp_tool,skill,agent_workflow`
- `conversation_id`: 可选，用于过滤会话绑定知识库

返回：

```json
{
  "items": [
    {
      "id": "rag.retrieve",
      "type": "rag",
      "name": "知识库检索",
      "description": "从绑定知识库中检索相关片段",
      "input_schema": {},
      "source": {
        "module": "rag"
      }
    },
    {
      "id": "skill.literature_search",
      "type": "skill",
      "name": "Literature Search",
      "input_schema": {}
    },
    {
      "id": "mcp.local-filesystem.search",
      "type": "mcp_tool",
      "name": "search"
    }
  ]
}
```

## 6. 关键服务设计

### 6.1 `services/capabilities`

#### `contracts.py`

```python
from pydantic import BaseModel, Field


class Capability(BaseModel):
    id: str
    type: str
    name: str
    description: str = ""
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    source: dict = Field(default_factory=dict)


class ToolCallRequest(BaseModel):
    capability_id: str
    input: dict = Field(default_factory=dict)
    conversation_id: str | None = None
    task_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class ToolCallResult(BaseModel):
    capability_id: str
    status: str
    output: dict = Field(default_factory=dict)
    citations: list[dict] = Field(default_factory=list)
    error: str = ""
    metadata: dict = Field(default_factory=dict)
```

#### `registry.py`

职责：

- 汇总内置 RAG 能力。
- 汇总启用的 MCP tools。
- 汇总启用的 Skills。
- 汇总 Agent workflows。

接口：

```python
class CapabilityRegistry:
    def list_capabilities(
        self,
        *,
        user_id: str,
        conversation_id: str | None = None,
        types: list[str] | None = None,
    ) -> list[Capability]:
        ...
```

#### `executor.py`

职责：

- 根据 `capability_id` 分发到 RAG / MCP / Skills / Agent。
- 统一记录 `paperchat_tool_invocation_logs`。
- 统一把失败包装成 `ToolCallResult`。

分发规则：

| capability_id 前缀 | 目标 |
|---|---|
| `rag.` | `services.rag.service` |
| `mcp.` | `services.mcp.tool_adapter` |
| `skill.` | `services.skills.executor` |
| `agent.` | `services.agents.service` |

### 6.2 `services/knowledge`

职责：

- 管理知识库和文件元数据。
- 管理会话绑定。
- 触发 RAG 索引任务。

核心方法：

```python
class KnowledgeService:
    def list_bases(self, user_id: str, status: str = "active") -> dict: ...
    def create_base(self, user_id: str, name: str, description: str) -> dict: ...
    def get_base(self, user_id: str, base_id: str) -> dict: ...
    def upload_file(self, user_id: str, base_id: str, upload_file) -> dict: ...
    def bind_conversation(self, user_id: str, conversation_id: str, base_id: str, binding_type: str) -> dict: ...
    def list_conversation_bindings(self, user_id: str, conversation_id: str) -> dict: ...
```

### 6.3 `services/rag`

RAG 不直接面向前端页面，而是给 Chat / Agents / Tasks 使用。

#### 索引流程

```text
Knowledge upload
  -> storage.save(file)
  -> knowledge_files.insert(parser_status=pending, index_status=pending)
  -> rag_index_jobs.insert(status=pending)
  -> tasks.runtime.enqueue(index_file_job)
  -> rag.pipeline.run(job_id)
  -> parser.parse(object_key)
  -> chunker.chunk(parsed_text)
  -> model_router.embed(route_key=embedding)
  -> vector_store.upsert(collection, vectors)
  -> knowledge_chunks.insert(...)
  -> knowledge_files.update(parser_status=completed, index_status=completed)
```

#### 检索流程

```text
Chat / Agent
  -> capability_executor.execute("rag.retrieve")
  -> rag_service.retrieve(query, conversation_id, knowledge_base_ids)
  -> resolve conversation bindings
  -> model_router.embed(query)
  -> vector_store.search(collections)
  -> load knowledge_chunks by vector_doc_id
  -> optional rerank
  -> return snippets + citation metadata
  -> write rag_retrieval_logs
```

核心方法：

```python
class RagService:
    async def index_file(self, *, user_id: str, knowledge_file_id: str, job_id: str) -> dict: ...

    async def retrieve(
        self,
        *,
        user_id: str,
        query: str,
        conversation_id: str | None = None,
        knowledge_base_ids: list[str] | None = None,
        top_k: int = 8,
    ) -> dict:
        ...
```

返回结构：

```json
{
  "query": "RAG evaluation",
  "items": [
    {
      "chunk_id": "chunk-id",
      "knowledge_file_id": "file-id",
      "title": "paper title",
      "snippet": "retrieved text",
      "score": 0.82,
      "locator": {
        "page_no": 3,
        "section_title": "Evaluation"
      }
    }
  ],
  "retrieval_log_id": "log-id"
}
```

### 6.4 `services/mcp`

职责：

- 管理 MCP 服务配置。
- 建立 MCP client。
- 刷新工具列表。
- 将 MCP tool 映射成 Capability。

核心方法：

```python
class McpService:
    def list_services(self, user_id: str) -> dict: ...
    def create_service(self, user_id: str, payload: dict) -> dict: ...
    def test_service(self, user_id: str, service_id: str) -> dict: ...
    async def refresh_tools(self, user_id: str, service_id: str) -> dict: ...


class McpToolAdapter:
    async def list_capabilities(self, user_id: str) -> list[Capability]: ...
    async def execute(self, user_id: str, capability_id: str, input: dict) -> ToolCallResult: ...
```

MCP capability id 规范：

```text
mcp.{server_id}.{tool_name}
```

### 6.5 `services/skills`

职责：

- 管理 Skill 配置。
- 加载 Skill manifest。
- 校验输入输出 schema。
- 执行 Skill。

Skill capability id 规范：

```text
skill.{skill_id}
```

执行流程：

```text
CapabilityExecutor
  -> SkillsExecutor.execute(skill_id, input)
  -> load skill config
  -> validate input_schema
  -> run entrypoint
  -> validate output_schema
  -> return ToolCallResult
```

核心方法：

```python
class SkillService:
    def list_skills(self, user_id: str) -> dict: ...
    def import_skill(self, user_id: str, source_uri: str) -> dict: ...
    def update_skill(self, user_id: str, skill_id: str, payload: dict) -> dict: ...
    def test_skill(self, user_id: str, skill_id: str, input: dict) -> dict: ...


class SkillExecutor:
    async def execute(self, *, user_id: str, skill_id: str, input: dict) -> ToolCallResult: ...
```

### 6.6 `services/model_router`

职责：

- 管理模型供应商。
- 管理模型槽位路由。
- 为 Chat / RAG / Skills / Agents 提供统一模型调用。
- 记录模型调用日志。

核心接口：

```python
class ModelRouter:
    async def complete(
        self,
        *,
        user_id: str,
        route_key: str,
        messages: list[dict],
        conversation_id: str | None = None,
        task_id: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        ...

    async def embed(
        self,
        *,
        user_id: str,
        texts: list[str],
        route_key: str = "embedding",
        metadata: dict | None = None,
    ) -> list[list[float]]:
        ...
```

调用完成后写入：

- `paperchat_model_invocation_logs`

失败时也写日志，`status=failed`，`error_code` 保留供应商错误码。

### 6.7 `services/tasks`

职责：

- 统一创建研究任务。
- 运行工作流。
- 记录 workflow run、node run、task event。
- 提供 SSE。

任务创建流程：

```text
POST /tasks
  -> research_tasks.insert(status=pending)
  -> workflow_runs.insert(status=pending)
  -> workflow_node_runs.insert(default nodes)
  -> task_events.insert(task.created)
  -> runtime.enqueue(task_id)
```

运行流程：

```text
runtime.run(task_id)
  -> update task/runs status=running
  -> event_bus.publish(task.started)
  -> for node in workflow:
       update node status=running
       publish node.started
       execute node with capability_executor/model_router/rag
       update node output/status
       publish node.completed
  -> write task_artifacts
  -> update task completed
  -> publish task.completed
```

SSE 需要同时支持：

1. 当前进程内订阅实时事件。
2. 连接恢复时从 `paperchat_task_events` 补发历史事件。

### 6.8 `services/dashboard`

Dashboard 不应该主动侵入业务流程。它只聚合日志：

- `paperchat_model_invocation_logs`
- `paperchat_tool_invocation_logs`
- `paperchat_research_tasks`
- `paperchat_workflow_node_runs`
- `paperchat_rag_retrieval_logs`

核心方法：

```python
class DashboardService:
    def overview(self, user_id: str, from_: datetime | None, to: datetime | None) -> dict: ...
    def model_usage(self, user_id: str, group_by: str, from_: datetime, to: datetime) -> dict: ...
    def task_distribution(self, user_id: str, from_: datetime, to: datetime) -> dict: ...
    def tool_usage(self, user_id: str, from_: datetime, to: datetime) -> dict: ...
```

## 7. Chat / Agents 与模块交换

### 7.1 Chat 使用知识库

Chat 当前发消息接口为：

```text
POST /api/v1/conversations/{conversation_id}/messages/stream
```

扩展逻辑：

1. 用户消息落库。
2. Chat service 根据 conversation_id 查询绑定知识库。
3. 模型通过 `tool_call` 路由判断是否需要 RAG。
4. 若需要，调用：

```python
capability_executor.execute(
    user_id=user_id,
    request=ToolCallRequest(
        capability_id="rag.retrieve",
        conversation_id=conversation_id,
        input={"query": content, "top_k": 8},
    ),
)
```

5. RAG 结果进入模型上下文。
6. Assistant 消息落库，同时保存 citations。
7. SSE 输出 `message.tool` 和 `message.completed`。

### 7.2 Agents 使用 Skills / MCP / RAG / Models

Agent 节点配置已有：

- `executor_key`
- `fallback_executor_key`
- `model_slot`
- `config_json`

建议把 `executor_key` 规范为 capability id：

```text
rag.retrieve
skill.{skill_id}
mcp.{server_id}.{tool_name}
agent.{workflow_id}
```

节点执行时：

```python
if node.executor_key:
    result = await capability_executor.execute(...)
else:
    result = await model_router.complete(route_key=node.model_slot, ...)
```

这样 Agent 页可以统一展示所有可选执行器。

### 7.3 Dashboard 采集

各模块只写日志，不直接调用 Dashboard：

- `model_router` 写 `model_invocation_logs`
- `capability_executor` 写 `tool_invocation_logs`
- `rag_service` 写 `rag_retrieval_logs`
- `tasks_service` 写 task / workflow / node 状态

Dashboard 查询时再聚合。

## 8. 状态枚举

### 8.1 通用状态

| 状态 | 含义 |
|---|---|
| `active` | 正常启用 |
| `archived` | 归档 |
| `disabled` | 禁用 |
| `deleted` | 软删除 |

### 8.2 文件解析状态

| 状态 | 含义 |
|---|---|
| `pending` | 等待解析 |
| `parsing` | 解析中 |
| `parsed` | 解析完成 |
| `failed` | 解析失败 |

### 8.3 索引状态

| 状态 | 含义 |
|---|---|
| `pending` | 等待索引 |
| `indexing` | 索引中 |
| `indexed` | 已索引 |
| `failed` | 索引失败 |

### 8.4 任务状态

沿用当前：

| 状态 | 含义 |
|---|---|
| `pending` | 待运行 |
| `running` | 运行中 |
| `completed` | 已完成 |
| `failed` | 失败 |
| `cancelled` | 已取消 |

## 9. 并行开发文件边界

### 9.1 Integration Agent

负责共享文件：

- `apps/backend/paperchat/api/v1/router.py`
- `apps/backend/paperchat/schemas/common.py`
- `apps/backend/paperchat/services/capabilities/*`
- `apps/backend/paperchat/database/models/__init__.py`
- `sql/mysql_init.sql`

### 9.2 Knowledge / RAG Agent

负责：

- `apps/backend/paperchat/api/v1/knowledge.py`
- `apps/backend/paperchat/schemas/knowledge.py`
- `apps/backend/paperchat/schemas/rag.py`
- `apps/backend/paperchat/services/knowledge/*`
- `apps/backend/paperchat/services/rag/*`
- `apps/backend/paperchat/database/models/knowledge.py`
- `apps/backend/paperchat/database/dao/knowledge.py`

### 9.3 MCP Agent

负责：

- `apps/backend/paperchat/api/v1/mcp.py`
- `apps/backend/paperchat/schemas/mcp.py`
- `apps/backend/paperchat/services/mcp/*`
- `apps/backend/paperchat/database/models/mcp.py`
- `apps/backend/paperchat/database/dao/mcp.py`

### 9.4 Skills Agent

负责：

- `apps/backend/paperchat/api/v1/skills.py`
- `apps/backend/paperchat/schemas/skills.py`
- `apps/backend/paperchat/services/skills/*`
- `apps/backend/paperchat/database/models/skills.py`
- `apps/backend/paperchat/database/dao/skills.py`

### 9.5 Models Agent

负责：

- `apps/backend/paperchat/api/v1/models.py`
- `apps/backend/paperchat/schemas/models.py`
- `apps/backend/paperchat/services/model_router/*`
- `apps/backend/paperchat/database/models/models.py`
- `apps/backend/paperchat/database/dao/models.py`

### 9.6 Tasks Agent

负责：

- `apps/backend/paperchat/api/v1/tasks.py`
- `apps/backend/paperchat/schemas/tasks.py`
- `apps/backend/paperchat/services/tasks/*`
- `apps/backend/paperchat/database/models/tasks.py`
- `apps/backend/paperchat/database/dao/tasks.py`

### 9.7 Dashboard Agent

负责：

- `apps/backend/paperchat/api/v1/dashboard.py`
- `apps/backend/paperchat/schemas/dashboard.py`
- `apps/backend/paperchat/services/dashboard/*`
- `apps/backend/paperchat/database/models/metrics.py`
- `apps/backend/paperchat/database/dao/metrics.py`

## 10. 落地顺序

### M1：共享骨架

1. 新增 `schemas/`。
2. 新增 `services/capabilities/`。
3. 新增模块 API 文件，占位返回空列表。
4. 在 `api/v1/router.py` 注册新 router。
5. 补齐数据库模型和初始化 SQL。

### M2：模型路由

1. 实现 providers/routes CRUD。
2. 实现 `ModelRouter.complete/embed` 抽象。
3. 写入 `paperchat_model_invocation_logs`。
4. Chat 逐步改为通过 `model_router` 调模型。

### M3：Knowledge + RAG

1. 实现知识库 CRUD。
2. 实现文件上传和 storage 保存。
3. 实现 index job。
4. 实现 parser/chunker/vector_store。
5. 实现 `rag.retrieve` capability。
6. Chat 通过会话绑定知识库执行检索。

### M4：MCP + Skills

1. 实现 MCP server CRUD、healthcheck、tools refresh。
2. 实现 Skill import、manifest 解析、schema 校验。
3. 注册 MCP / Skills 到 capability registry。
4. Agents 节点配置页可选择这些能力。

### M5：Tasks

1. 实现 `/tasks` 统一入口。
2. 实现 task events 表。
3. 实现 SSE 补发和实时订阅。
4. Agent workflow run 统一写入 task/node/artifact。

### M6：Dashboard

1. 聚合模型日志。
2. 聚合工具日志。
3. 聚合任务状态和节点运行。
4. 输出 overview、趋势和分布接口。

## 11. 测试策略

### 单元测试

- `rag.chunker`：切片边界、页码定位。
- `skills.validator`：输入输出 schema。
- `model_router.router`：route_key 解析和 fallback。
- `capabilities.executor`：分发和错误包装。

### API 测试

- Knowledge CRUD + upload。
- MCP create/test/refresh-tools。
- Skills import/test。
- Models route/test。
- Tasks create/events。
- Dashboard overview。

### 集成测试

1. 创建知识库。
2. 上传文件并完成索引。
3. 创建会话绑定知识库。
4. 发送聊天消息触发 RAG。
5. 创建研究任务。
6. 任务节点调用 RAG/Skill/MCP。
7. 看板出现模型调用、工具调用、任务分布。

## 12. 关键约束

1. 敏感配置不明文回显。API key、MCP env secret 后续应迁移到 secret store，MySQL 只保存引用。
2. RAG 索引和任务执行必须异步化，API 只返回 job/task id。
3. 所有跨模块调用必须经过 `capabilities` 或 `model_router`。
4. Dashboard 只读日志，不参与业务流程。
5. 新增表和 ORM 命名必须使用 `paperchat_` 前缀。
6. 前端模块接口不要暴露内部实现细节，例如 vector collection、embedding provider secret。
