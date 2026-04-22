from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from paperchat.workflows.nodes import (
    build_analyse_node,
    build_reading_node,
    build_report_node,
    build_search_node,
    build_writing_node,
)
from paperchat.workflows.state import ResearchWorkflowState, WorkflowNodeExecutionError


def build_research_workflow_graph(task_service):
    graph = StateGraph(ResearchWorkflowState)
    graph.add_node("search_node", build_search_node(task_service))
    graph.add_node("reading_node", build_reading_node(task_service))
    graph.add_node("analyse_node", build_analyse_node(task_service))
    graph.add_node("writing_node", build_writing_node(task_service))
    graph.add_node("report_node", build_report_node(task_service))
    graph.add_edge(START, "search_node")
    graph.add_edge("search_node", "reading_node")
    graph.add_edge("reading_node", "analyse_node")
    graph.add_edge("analyse_node", "writing_node")
    graph.add_edge("writing_node", "report_node")
    graph.add_edge("report_node", END)
    return graph.compile()


async def run_research_workflow(
    *,
    task_service,
    task_id: str,
    user_id: str,
    workspace_id: str,
    topic: str,
    keywords: list[str] | None = None,
    source_config: dict | None = None,
) -> dict:
    graph = build_research_workflow_graph(task_service)
    initial_state: ResearchWorkflowState = {
        "task_id": task_id,
        "user_id": user_id,
        "workspace_id": workspace_id,
        "topic": topic,
        "keywords": keywords or [],
        "source_config": source_config or {},
        "search_queries": [],
        "papers": [],
        "reading_notes": [],
        "analysis_clusters": [],
        "deep_analysis_results": [],
        "analysis_markdown": "",
        "writing_outline": [],
        "writing_sections": [],
        "report_markdown": "",
        "report_summary": "",
        "last_detail": "",
        "failed_node": None,
        "error": None,
    }

    await task_service.mark_workflow_started(task_id)
    try:
        result = await graph.ainvoke(initial_state)
    except WorkflowNodeExecutionError as exc:
        await task_service.mark_task_failed(task_id=task_id, node_id=exc.node_id, detail=exc.message)
        raise
    except Exception as exc:
        await task_service.mark_task_failed(task_id=task_id, node_id=None, detail=f"工作流执行失败：{exc}")
        raise

    detail = result.get("last_detail", "任务已完成")
    await task_service.mark_task_completed(task_id=task_id, detail=detail)
    return result
