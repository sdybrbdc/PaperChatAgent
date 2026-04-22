from __future__ import annotations

from dataclasses import dataclass


DEFAULT_WORKFLOW_ID = "paperchat-default-workflow"
DEFAULT_WORKFLOW_NAME = "PaperChatAgent 默认研究工作流"
DEFAULT_WORKFLOW_DESCRIPTION = "搜索、阅读、分析、写作、报告五阶段研究智能体工作流。"


@dataclass(frozen=True, slots=True)
class WorkflowNodeDefinition:
    id: str
    title: str
    description: str
    order: int
    progress_percent: float
    tone: str = "default"
    agent_names: tuple[str, ...] = ()

    def as_payload(
        self,
        *,
        status: str = "idle",
        detail: str = "",
        started_at: str | None = None,
        completed_at: str | None = None,
    ) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": status,
            "detail": detail,
            "order": self.order,
            "tone": self.tone,
            "progress_percent": self.progress_percent,
            "agent_names": list(self.agent_names),
            "started_at": started_at,
            "completed_at": completed_at,
        }


DEFAULT_WORKFLOW_NODES = (
    WorkflowNodeDefinition(
        id="search_agent_node",
        title="搜索节点",
        description="收束研究主题并生成检索查询，拉取候选论文。",
        order=1,
        progress_percent=20.0,
        agent_names=("search_agent",),
    ),
    WorkflowNodeDefinition(
        id="reading_agent_node",
        title="阅读节点",
        description="整理论文摘要与元数据，形成可分析的阅读卡片。",
        order=2,
        progress_percent=45.0,
        agent_names=("reading_agent",),
    ),
    WorkflowNodeDefinition(
        id="analyse_agent_node",
        title="分析节点",
        description="汇总候选论文主题、趋势与代表性发现。",
        order=3,
        progress_percent=70.0,
        agent_names=("cluster_agent", "deep_analyse_agent", "global_analyse_agent"),
    ),
    WorkflowNodeDefinition(
        id="writing_agent_node",
        title="写作节点",
        description="把分析结论扩展成章节草稿与输出骨架。",
        order=4,
        progress_percent=85.0,
        agent_names=("writing_director_agent", "retrieval_agent", "writing_agent", "review_agent"),
    ),
    WorkflowNodeDefinition(
        id="report_agent_node",
        title="报告节点",
        description="组装最终 Markdown 报告并沉淀任务产物。",
        order=5,
        progress_percent=100.0,
        agent_names=("report_agent",),
    ),
)


def get_workflow_definition(workflow_id: str) -> dict | None:
    if workflow_id != DEFAULT_WORKFLOW_ID:
        return None
    return {
        "id": DEFAULT_WORKFLOW_ID,
        "name": DEFAULT_WORKFLOW_NAME,
        "description": DEFAULT_WORKFLOW_DESCRIPTION,
        "node_count": len(DEFAULT_WORKFLOW_NODES),
        "agent_runtime": "langgraph",
        "node_ids": [node.id for node in DEFAULT_WORKFLOW_NODES],
    }


def build_workflow_payload(workflow_id: str) -> dict | None:
    return get_workflow_definition(workflow_id)


def list_workflow_payloads() -> list[dict]:
    workflow = get_workflow_definition(DEFAULT_WORKFLOW_ID)
    return [workflow] if workflow else []


def build_node_payloads(node_runs: list[dict] | None = None) -> list[dict]:
    run_map = {item["id"]: item for item in (node_runs or [])}
    payloads: list[dict] = []
    for node in DEFAULT_WORKFLOW_NODES:
        current = run_map.get(node.id, {})
        payloads.append(
            node.as_payload(
                status=str(current.get("status", "idle")),
                detail=str(current.get("detail", "")),
                started_at=current.get("started_at"),
                completed_at=current.get("completed_at"),
            )
        )
    return payloads
