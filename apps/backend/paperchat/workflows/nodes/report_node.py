from __future__ import annotations

from paperchat.workflows.agents import ReportAgent
from paperchat.workflows.definitions import DEFAULT_WORKFLOW_NODES
from paperchat.workflows.state import ResearchWorkflowState, WorkflowNodeExecutionError


NODE = DEFAULT_WORKFLOW_NODES[4]


def _build_summary(report_markdown: str) -> str:
    lines = [line.strip() for line in report_markdown.splitlines() if line.strip()]
    for line in lines:
        if not line.startswith("#"):
            return line[:180]
    return (lines[0] if lines else "研究报告已生成")[:180]


def build_report_node(task_service):
    agent = ReportAgent()

    async def report_node(state: ResearchWorkflowState) -> dict:
        task_id = state["task_id"]
        try:
            await task_service.mark_node_started(task_id=task_id, node_id=NODE.id, detail="正在组装最终报告")
            report_markdown = await agent.build_report(
                topic=state["topic"],
                sections=state.get("writing_sections", []),
            )
            report_summary = _build_summary(report_markdown)
            await task_service.save_report(
                task_id=task_id,
                title=state["topic"],
                content_markdown=report_markdown,
                summary=report_summary,
            )
            detail = "报告生成完成，已保存 Markdown 产物"
            await task_service.mark_node_completed(task_id=task_id, node_id=NODE.id, detail=detail)
            return {
                "report_markdown": report_markdown,
                "report_summary": report_summary,
                "last_detail": detail,
            }
        except Exception as exc:
            raise WorkflowNodeExecutionError(node_id=NODE.id, message=f"报告节点失败：{exc}") from exc

    return report_node
