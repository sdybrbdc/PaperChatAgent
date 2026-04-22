from __future__ import annotations

from paperchat.workflows.agents import WritingAgent
from paperchat.workflows.definitions import DEFAULT_WORKFLOW_NODES
from paperchat.workflows.state import ResearchWorkflowState, WorkflowNodeExecutionError


NODE = DEFAULT_WORKFLOW_NODES[3]


def build_writing_node(task_service):
    agent = WritingAgent()

    async def writing_node(state: ResearchWorkflowState) -> dict:
        task_id = state["task_id"]
        try:
            await task_service.mark_node_started(task_id=task_id, node_id=NODE.id, detail="正在组织章节草稿")

            async def progress_callback(stage: str, detail: str) -> None:
                await task_service.mark_node_progress(task_id=task_id, node_id=NODE.id, detail=detail)

            outline, sections = await agent.run_full_writing(
                topic=state["topic"],
                reading_notes=state.get("reading_notes", []),
                deep_analysis_results=state.get("deep_analysis_results", []),
                analysis_markdown=state.get("analysis_markdown", ""),
                progress_callback=progress_callback,
            )
            detail = f"写作完成，已整理 {len(sections)} 个章节"
            await task_service.mark_node_completed(task_id=task_id, node_id=NODE.id, detail=detail)
            return {
                "writing_outline": outline,
                "writing_sections": sections,
                "last_detail": detail,
            }
        except Exception as exc:
            raise WorkflowNodeExecutionError(node_id=NODE.id, message=f"写作节点失败：{exc}") from exc

    return writing_node
