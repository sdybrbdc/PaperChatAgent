from __future__ import annotations

from collections.abc import Awaitable, Callable
from copy import deepcopy
from dataclasses import dataclass

from langgraph.graph import END, START, StateGraph

from paperchat.database.dao import memory_store
from paperchat.providers import temporary_model_slot_overrides
from paperchat.workflows.definitions import DEFAULT_WORKFLOW_NODES, WorkflowNodeDefinition
from paperchat.workflows.nodes import (
    build_analyse_node,
    build_reading_node,
    build_report_node,
    build_search_node,
    build_writing_node,
)
from paperchat.workflows.state import ResearchWorkflowState, WorkflowNodeExecutionError


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    definition: WorkflowNodeDefinition
    runner: Callable[[ResearchWorkflowState], Awaitable[dict]]


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


def build_research_workflow_steps(task_service) -> list[WorkflowStep]:
    node_map = {node.id: node for node in DEFAULT_WORKFLOW_NODES}
    return [
        WorkflowStep(definition=node_map["search_agent_node"], runner=build_search_node(task_service)),
        WorkflowStep(definition=node_map["reading_agent_node"], runner=build_reading_node(task_service)),
        WorkflowStep(definition=node_map["analyse_agent_node"], runner=build_analyse_node(task_service)),
        WorkflowStep(definition=node_map["writing_agent_node"], runner=build_writing_node(task_service)),
        WorkflowStep(definition=node_map["report_agent_node"], runner=build_report_node(task_service)),
    ]


def _build_initial_state(
    *,
    task_id: str,
    user_id: str,
    workspace_id: str,
    topic: str,
    keywords: list[str],
    source_config: dict,
) -> ResearchWorkflowState:
    return {
        "task_id": task_id,
        "user_id": user_id,
        "workspace_id": workspace_id,
        "topic": topic,
        "keywords": keywords,
        "source_config": source_config,
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


def _resolve_resume_index(steps: list[WorkflowStep], resume_from_node: str | None) -> int:
    if not resume_from_node:
        return 0
    for index, step in enumerate(steps):
        if step.definition.id == resume_from_node:
            return index
    return 0


async def _execute_step_with_recovery(
    *,
    task_service,
    task_id: str,
    step: WorkflowStep,
    state: ResearchWorkflowState,
    recovery_policy: dict,
    checkpoint: dict,
) -> ResearchWorkflowState | None:
    max_retries = max(0, int(recovery_policy.get("max_retries_per_node", 2)))
    fallback_overrides = list(recovery_policy.get("fallback_model_overrides", {}).get(step.definition.id, []))
    initial_overrides = dict(checkpoint.get("active_model_overrides", {}))
    variant_overrides: list[dict[str, str]] = []
    variant_overrides.append(initial_overrides)
    for candidate in fallback_overrides:
        candidate_dict = dict(candidate)
        if candidate_dict != initial_overrides and candidate_dict not in variant_overrides:
            variant_overrides.append(candidate_dict)

    attempt_count = 0
    last_error_message = ""
    for variant_index, overrides in enumerate(variant_overrides):
        attempt_label = f"主模型配置" if variant_index == 0 and not overrides else f"备用模型配置 {variant_index}"
        for retry_index in range(max_retries + 1):
            attempt_count += 1
            if attempt_count > 1:
                detail = f"{step.definition.title} 第 {attempt_count} 次尝试，当前使用 {attempt_label}"
                await task_service.mark_node_retrying(task_id=task_id, node_id=step.definition.id, detail=detail)
            memory_store.update_task_node_run(
                task_id,
                step.definition.id,
                attempt_count=attempt_count,
                input_snapshot_json=deepcopy(state),
                checkpoint_json={"workflow_state": deepcopy(state)},
                active_model_overrides=overrides,
            )
            try:
                with temporary_model_slot_overrides(overrides):
                    partial_state = await step.runner(state)
            except WorkflowNodeExecutionError as exc:
                last_error_message = exc.message
            except Exception as exc:  # pragma: no cover - defensive fallback
                last_error_message = f"{step.definition.title} 执行异常：{exc}"
            else:
                next_state = deepcopy(state)
                next_state.update(partial_state)
                memory_store.update_task_workflow_state(task_id, next_state)
                memory_store.update_task_node_run(
                    task_id,
                    step.definition.id,
                    output_snapshot_json=deepcopy(partial_state),
                    checkpoint_json={"workflow_state": deepcopy(next_state)},
                    last_error_code="",
                    last_error_message="",
                    active_model_overrides=overrides,
                )
                memory_store.update_task_checkpoint(
                    task_id,
                    resume_from_node=None,
                    failure_context={},
                    active_model_overrides=overrides,
                )
                return next_state

            memory_store.update_task_node_run(
                task_id,
                step.definition.id,
                last_error_code="NODE_EXECUTION_FAILED",
                last_error_message=last_error_message,
                checkpoint_json={"workflow_state": deepcopy(state)},
                active_model_overrides=overrides,
            )

    failure_context = {
        "node_id": step.definition.id,
        "node_title": step.definition.title,
        "error_code": "NODE_EXECUTION_FAILED",
        "error_message": last_error_message,
        "attempt_count": attempt_count,
        "fallback_model_overrides": fallback_overrides,
    }
    memory_store.record_task_failure_context(
        task_id,
        resume_from_node=step.definition.id,
        failure_context=failure_context,
        active_model_overrides=variant_overrides[-1] if variant_overrides else {},
    )
    await task_service.mark_task_paused(
        task_id=task_id,
        node_id=step.definition.id,
        detail=f"{step.definition.title} 已暂停，等待恢复：{last_error_message}",
    )
    return None


async def run_research_workflow(
    *,
    task_service,
    task_id: str,
    user_id: str,
    workspace_id: str,
    topic: str,
    keywords: list[str] | None = None,
    source_config: dict | None = None,
    resume_from_node: str | None = None,
) -> dict:
    keywords = keywords or []
    source_config = source_config or {}
    steps = build_research_workflow_steps(task_service)
    checkpoint = memory_store.get_task_checkpoint(task_id)
    state = deepcopy(checkpoint.get("workflow_state") or {})
    if not state:
        state = _build_initial_state(
            task_id=task_id,
            user_id=user_id,
            workspace_id=workspace_id,
            topic=topic,
            keywords=keywords,
            source_config=source_config,
        )
        memory_store.update_task_workflow_state(task_id, state)

    recovery_policy = dict(checkpoint.get("recovery_policy") or {})
    if not recovery_policy:
        recovery_policy = task_service._build_recovery_policy(source_config)
        memory_store.update_task_checkpoint(task_id, recovery_policy=recovery_policy)

    resume_from_node = resume_from_node or checkpoint.get("resume_from_node")
    await task_service.mark_workflow_started(task_id)

    for step in steps[_resolve_resume_index(steps, resume_from_node) :]:
        next_state = await _execute_step_with_recovery(
            task_service=task_service,
            task_id=task_id,
            step=step,
            state=state,
            recovery_policy=recovery_policy,
            checkpoint=memory_store.get_task_checkpoint(task_id),
        )
        if next_state is None:
            return state
        state = next_state

    detail = state.get("last_detail", "任务已完成")
    await task_service.mark_task_completed(task_id=task_id, detail=detail)
    return state
