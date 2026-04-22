from __future__ import annotations

from paperchat.workflows.agents import AnalysisAgent
from paperchat.workflows.definitions import DEFAULT_WORKFLOW_NODES
from paperchat.workflows.state import ResearchWorkflowState, WorkflowNodeExecutionError


NODE = DEFAULT_WORKFLOW_NODES[2]


def build_analyse_node(task_service):
    agent = AnalysisAgent()

    async def analyse_node(state: ResearchWorkflowState) -> dict:
        task_id = state["task_id"]
        try:
            await task_service.mark_node_started(task_id=task_id, node_id=NODE.id, detail="正在聚合主题分析")

            async def progress_callback(stage: str, detail: str) -> None:
                await task_service.mark_node_progress(task_id=task_id, node_id=NODE.id, detail=detail)

            analysis_markdown, analysis_clusters, deep_analysis_results = await agent.run_full_analysis(
                topic=state["topic"],
                keywords=state.get("keywords", []),
                reading_notes=state.get("reading_notes", []),
                progress_callback=progress_callback,
            )
            detail = "分析完成，已生成主题概览与研究缺口总结"
            await task_service.mark_node_completed(task_id=task_id, node_id=NODE.id, detail=detail)
            return {
                "analysis_clusters": analysis_clusters,
                "deep_analysis_results": deep_analysis_results,
                "analysis_markdown": analysis_markdown,
                "last_detail": detail,
            }
        except Exception as exc:
            raise WorkflowNodeExecutionError(node_id=NODE.id, message=f"分析节点失败：{exc}") from exc

    return analyse_node
