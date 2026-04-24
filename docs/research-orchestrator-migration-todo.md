# Research Orchestrator 待补清单

## 已完成

- 后端目录收口为两层结构：
  - `apps/backend/paperchat/agents/research_orchestrator/` 承载节点与子能力实现
  - `apps/backend/paperchat/workflows/research_orchestrator/` 承载 LangGraph 主编排
- `services/agents/` 源码层只保留 `service.py` 和 `__init__.py`
- 内置工作流定义迁入 `agents/research_orchestrator/definition.py`
- Agent 仓储迁入 `services/agent_repository.py`
- 已实现状态模型、运行上下文、统一 prompt 管理
- 已实现主链路节点：`search -> reading -> analyse -> writing -> report`
- 已实现分析子节点：`analyse.cluster / analyse.deep_analyse / analyse.global_analyse`
- 已实现写作子节点：`writing.writing_director / writing.parallel_writing / writing.retrieval / writing.review`
- 已把 workflow runner 接回 `services/agents/service.py`
- 节点模型调用已切到 AutoGen：主节点/写作子节点默认 conversation client，分析子节点默认 reasoning client

## 仍需后续补齐

- 知识库写入能力：`reading` 现在只记录 `missing_tools=["temporary_knowledge_base_write"]`
- 知识库检索能力：`writing.retrieval` 现在只记录 `missing_tools=["knowledge_base_retrieval"]`
- `executor_key / fallback_executor_key` 驱动的跨 Agent 动态执行切换
- 更细粒度的节点流式进度事件，目前主要落库节点状态和结构化输出
- 端到端运行 smoke test 需要可用数据库、模型配置和 arXiv 网络环境

## 当前运行约定

- 运行时名称固定为 `research_orchestrator`
- 内置智能体 slug 仍为 `smart_research_assistant`
- 默认主流程不改变节点 ID 和执行顺序
- 模型 client 统一来自 `paperchat.providers`
- LLM 节点通过 `get_autogen_conversation_model_client()` / `get_autogen_reasoning_model_client()` 执行
- embedding 聚类继续通过 `get_embedding_client()` 执行
- retrieval/knowledge base 缺失能力不会阻断主流程，会写入 `missing_tools` 和 `skipped_capabilities`
