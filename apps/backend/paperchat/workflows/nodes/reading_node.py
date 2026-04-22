from __future__ import annotations

from paperchat.workflows.agents import ReadingAgent
from paperchat.workflows.definitions import DEFAULT_WORKFLOW_NODES
from paperchat.workflows.state import ResearchWorkflowState, WorkflowNodeExecutionError


NODE = DEFAULT_WORKFLOW_NODES[1]


def build_reading_node(task_service):
    agent = ReadingAgent()

    async def reading_node(state: ResearchWorkflowState) -> dict:
        task_id = state["task_id"]
        try:
            await task_service.mark_node_started(task_id=task_id, node_id=NODE.id, detail="正在提取阅读卡片")
            notes = agent.extract_notes(
                topic=state["topic"],
                keywords=state.get("keywords", []),
                papers=state.get("papers", []),
            )
            detail = f"阅读完成，生成 {len(notes)} 张阅读卡片"
            await task_service.mark_node_completed(task_id=task_id, node_id=NODE.id, detail=detail)
            return {
                "reading_notes": notes,
                "last_detail": detail,
            }
        except Exception as exc:
            raise WorkflowNodeExecutionError(node_id=NODE.id, message=f"阅读节点失败：{exc}") from exc

    return reading_node
