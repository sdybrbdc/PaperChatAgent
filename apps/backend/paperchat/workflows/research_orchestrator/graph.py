from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from paperchat.agents.research_orchestrator.analyse_agent import analyse_node
from paperchat.agents.research_orchestrator.reading_agent import reading_node
from paperchat.agents.research_orchestrator.report_agent import report_node
from paperchat.agents.research_orchestrator.runtime_support import ResearchRunContext, compact_json
from paperchat.agents.research_orchestrator.search_agent import search_node
from paperchat.agents.research_orchestrator.state_models import NodeError, PaperAgentState, State
from paperchat.agents.research_orchestrator.writing_agent import writing_node


def _error_field(node_id: str) -> str:
    return {
        "search": "search_node_error",
        "reading": "reading_node_error",
        "analyse": "analyse_node_error",
        "writing": "writing_node_error",
        "report": "report_node_error",
    }[node_id]


async def _run_top_node(
    state: State,
    *,
    context: ResearchRunContext,
    node_id: Literal["search", "reading", "analyse", "writing", "report"],
    detail: str,
    task_progress: int,
    action,
) -> State:
    current = state["value"]
    context.start_node(node_id, detail=detail, input_json=current.model_dump(mode="json"), progress=task_progress)
    try:
        result = await action(current)
        node_error = getattr(current.error, _error_field(node_id))
        if node_error:
            context.fail_node(node_id, message=str(node_error), output_json=result.get("output") or result)
        else:
            context.complete_node(
                node_id,
                detail=str(result.get("detail") or "completed"),
                output_json=result.get("output") or result,
                task_progress=task_progress,
            )
        context.update_checkpoint(current.model_dump(mode="json"))
    except Exception as exc:
        message = f"{node_id} failed: {exc}"
        setattr(current.error, _error_field(node_id), message)
        context.fail_node(node_id, message=message)
        context.update_checkpoint(current.model_dump(mode="json"))
    return {"run_id": state["run_id"], "value": current}


def _route_after(node_name: str):
    def _route(state: State) -> str:
        if state["value"].error.has_error():
            return "error_node"
        return node_name

    return _route


def build_research_orchestrator_graph(*, context: ResearchRunContext):
    async def run_search(state: State) -> State:
        model_slot = context.model_slot_for("search")
        return await _run_top_node(
            state,
            context=context,
            node_id="search",
            detail="正在生成检索条件并搜索 arXiv",
            task_progress=12,
            action=lambda value: search_node(value, model_slot=model_slot),
        )

    async def run_reading(state: State) -> State:
        model_slot = context.model_slot_for("reading")
        return await _run_top_node(
            state,
            context=context,
            node_id="reading",
            detail="正在抽取论文结构化信息",
            task_progress=30,
            action=lambda value: reading_node(value, model_slot=model_slot),
        )

    async def run_analyse(state: State) -> State:
        model_slot = context.model_slot_for("analyse", "reasoning_model")
        return await _run_top_node(
            state,
            context=context,
            node_id="analyse",
            detail="正在执行主题聚类、深度分析和全局分析",
            task_progress=55,
            action=lambda value: analyse_node(value, model_slot=model_slot, context=context),
        )

    async def run_writing(state: State) -> State:
        model_slot = context.model_slot_for("writing")
        return await _run_top_node(
            state,
            context=context,
            node_id="writing",
            detail="正在规划并生成报告章节",
            task_progress=78,
            action=lambda value: writing_node(value, model_slot=model_slot, context=context),
        )

    async def run_report(state: State) -> State:
        model_slot = context.model_slot_for("report")
        return await _run_top_node(
            state,
            context=context,
            node_id="report",
            detail="正在组装最终 Markdown 报告",
            task_progress=95,
            action=lambda value: report_node(value, model_slot=model_slot),
        )

    async def error_node(state: State) -> State:
        return state

    graph = StateGraph(State)
    graph.add_node("search_node", run_search)
    graph.add_node("reading_node", run_reading)
    graph.add_node("analyse_node", run_analyse)
    graph.add_node("writing_node", run_writing)
    graph.add_node("report_node", run_report)
    graph.add_node("error_node", error_node)
    graph.add_edge(START, "search_node")
    graph.add_conditional_edges("search_node", _route_after("reading_node"))
    graph.add_conditional_edges("reading_node", _route_after("analyse_node"))
    graph.add_conditional_edges("analyse_node", _route_after("writing_node"))
    graph.add_conditional_edges("writing_node", _route_after("report_node"))
    graph.add_conditional_edges("report_node", lambda state: "error_node" if state["value"].error.has_error() else END)
    graph.add_edge("error_node", END)
    return graph.compile()


async def run_research_orchestrator(*, run_id: str) -> dict[str, Any]:
    context = ResearchRunContext(run_id=run_id)
    run_input = context.run.input_json or {}
    state = PaperAgentState(
        user_request=str(run_input.get("request") or run_input.get("topic") or ""),
        max_papers=int(run_input.get("max_papers") or 6),
        error=NodeError(),
    )
    graph = build_research_orchestrator_graph(context=context)
    context.start_run()
    try:
        result = await graph.ainvoke({"run_id": run_id, "value": state})
        final_state: PaperAgentState = result["value"]
        if final_state.error.has_error():
            message = final_state.error.message()
            context.fail_run(message=message, error=final_state.error.model_dump(exclude_none=True))
            return {"status": "failed", "error": message}

        output = {
            "summary": final_state.report_summary,
            "report_markdown": final_state.report_markdown,
            "missing_tools": final_state.missing_tools,
            "skipped_capabilities": final_state.skipped_capabilities,
            "checkpoint": final_state.model_dump(mode="json"),
        }
        context.create_report_artifact(
            title="Research Orchestrator 研究报告",
            content=final_state.report_markdown,
            metadata={
                "summary": final_state.report_summary,
                "missing_tools": final_state.missing_tools,
                "skipped_capabilities": final_state.skipped_capabilities,
            },
        )
        context.complete_run(output=output, summary=final_state.report_summary)
        return {"status": "completed", "output": output}
    except Exception as exc:
        message = f"Research orchestrator failed: {exc}"
        context.fail_run(message=message, error={"message": message, "checkpoint": compact_json(state.model_dump(mode="json"))})
        return {"status": "failed", "error": message}
