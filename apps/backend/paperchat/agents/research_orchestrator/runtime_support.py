from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from typing import Any

from autogen_agentchat.agents import AssistantAgent

from paperchat.database.dao import memory_store
from paperchat.providers import (
    get_autogen_conversation_model_client,
    get_autogen_reasoning_model_client,
    temporary_model_slot_overrides,
)
from paperchat.services.agent_repository import agent_repository, utcnow


def message_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in content)
    return str(content)


def extract_json_object(text: str) -> Any:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", clean, flags=re.S)
        if match:
            return json.loads(match.group(1))
        raise


def compact_json(value: Any, *, limit: int = 6000) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def summarize_text(text: str, *, limit: int = 480) -> str:
    stripped = re.sub(r"\s+", " ", text or "").strip()
    return stripped[:limit] + ("..." if len(stripped) > limit else "")


async def call_autogen_agent(
    *,
    name: str,
    system_prompt: str,
    user_prompt: str,
    model_slot: str = "conversation_model",
    reasoning: bool = False,
) -> str:
    source_slot = "reasoning_model" if reasoning else "conversation_model"

    async def _run() -> str:
        model_client = get_autogen_reasoning_model_client() if reasoning else get_autogen_conversation_model_client()
        agent = AssistantAgent(
            name=name,
            model_client=model_client,
            system_message=system_prompt,
        )
        try:
            result = await agent.run(task=user_prompt)
            messages = getattr(result, "messages", []) or []
            if not messages:
                return ""
            return message_to_text(getattr(messages[-1], "content", messages[-1])).strip()
        finally:
            close = getattr(model_client, "close", None)
            if close is not None:
                maybe_awaitable = close()
                if hasattr(maybe_awaitable, "__await__"):
                    await maybe_awaitable

    if model_slot and model_slot != source_slot:
        with temporary_model_slot_overrides({source_slot: model_slot}):
            return await _run()
    return await _run()


class ResearchRunContext:
    def __init__(self, *, run_id: str) -> None:
        self.run_id = run_id
        self.run = agent_repository.get_run(run_id)
        if self.run is None:
            raise RuntimeError(f"Workflow run not found: {run_id}")
        self.task = agent_repository.get_task(self.run.task_id)
        if self.task is None:
            raise RuntimeError(f"Research task not found: {self.run.task_id}")
        self.workflow = agent_repository.get_workflow(self.run.workflow_id)
        self.node_overrides = {
            item.node_id: item
            for item in agent_repository.list_config_overrides(user_id=self.run.user_id, workflow_id=self.run.workflow_id)
        }

    def model_slot_for(self, node_id: str, default: str = "conversation_model") -> str:
        override = self.node_overrides.get(node_id)
        return override.model_slot if override and override.model_slot else default

    def start_run(self) -> None:
        now = utcnow()
        agent_repository.update_task(self.task.id, status="running", progress=1, current_node="search")
        agent_repository.update_run(self.run_id, status="running", started_at=now, current_node="search")

    def complete_run(self, *, output: dict[str, Any], summary: str) -> None:
        now = utcnow()
        agent_repository.update_task(
            self.task.id,
            status="completed",
            progress=100,
            current_node="report",
            summary=summary,
            completed_at=now,
        )
        agent_repository.update_run(
            self.run_id,
            status="completed",
            output_json=output,
            current_node="report",
            completed_at=now,
        )
        if self.run.conversation_id:
            memory_store.add_message(
                conversation_id=self.run.conversation_id,
                user_id=self.run.user_id,
                role="assistant",
                message_type="agent_result",
                content=(
                    "智能研究助手已完成报告生成。\n\n"
                    f"- 任务：{self.task.title}\n"
                    f"- 摘要：{summary}\n"
                    f"- 查看详情：/agents/runs/{self.run_id}"
                ),
                metadata={"workflow_run_id": self.run_id, "task_id": self.task.id},
            )

    def fail_run(self, *, message: str, error: dict[str, Any] | None = None) -> None:
        now = utcnow()
        agent_repository.update_task(
            self.task.id,
            status="failed",
            failed_reason=message,
            completed_at=now,
        )
        agent_repository.update_run(
            self.run_id,
            status="failed",
            error_json=error or {"message": message},
            completed_at=now,
        )

    def update_checkpoint(self, value: dict[str, Any]) -> None:
        agent_repository.update_run(self.run_id, checkpoint_json=value)

    def start_node(self, node_id: str, *, detail: str, input_json: dict[str, Any] | None = None, progress: int = 0) -> None:
        now = utcnow()
        agent_repository.update_task(self.task.id, current_node=node_id, progress=progress)
        agent_repository.update_run(self.run_id, current_node=node_id)
        agent_repository.update_node_run(
            workflow_run_id=self.run_id,
            node_id=node_id,
            status="running",
            detail=detail,
            progress=0,
            input_json=input_json or {},
            started_at=now,
        )

    def complete_node(
        self,
        node_id: str,
        *,
        detail: str,
        output_json: dict[str, Any] | None = None,
        progress: int = 100,
        task_progress: int | None = None,
    ) -> None:
        now = utcnow()
        if task_progress is not None:
            agent_repository.update_task(self.task.id, progress=task_progress, current_node=node_id)
        agent_repository.update_node_run(
            workflow_run_id=self.run_id,
            node_id=node_id,
            status="completed",
            detail=detail,
            progress=progress,
            output_json=output_json or {},
            completed_at=now,
        )

    def fail_node(self, node_id: str, *, message: str, output_json: dict[str, Any] | None = None) -> None:
        now = utcnow()
        agent_repository.update_node_run(
            workflow_run_id=self.run_id,
            node_id=node_id,
            status="failed",
            detail=message,
            error_text=message,
            output_json=output_json or {},
            completed_at=now,
        )

    def create_report_artifact(self, *, title: str, content: str, metadata: dict[str, Any]) -> None:
        agent_repository.create_artifact(
            task_id=self.task.id,
            workflow_run_id=self.run_id,
            artifact_type="markdown_report",
            title=title,
            content=content,
            metadata=metadata,
        )


async def run_node_with_status(
    *,
    context: ResearchRunContext,
    node_id: str,
    detail: str,
    task_progress: int,
    input_json: dict[str, Any] | None,
    action: Callable[[], Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    context.start_node(node_id, detail=detail, input_json=input_json, progress=task_progress)
    try:
        result = await action()
    except Exception as exc:
        message = f"{node_id} failed: {exc}"
        context.fail_node(node_id, message=message)
        raise
    context.complete_node(
        node_id,
        detail=result.get("detail", "completed"),
        output_json=result.get("output", result),
        task_progress=task_progress,
    )
    return result


async def gather_limited(limit: int, tasks: list[Callable[[], Awaitable[Any]]]) -> list[Any]:
    semaphore = asyncio.Semaphore(limit)

    async def _run(task: Callable[[], Awaitable[Any]]) -> Any:
        async with semaphore:
            return await task()

    return await asyncio.gather(*[_run(task) for task in tasks])
