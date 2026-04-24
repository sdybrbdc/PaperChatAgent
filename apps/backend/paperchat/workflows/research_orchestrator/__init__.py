from __future__ import annotations

from collections.abc import Awaitable, Callable

from paperchat.agents.research_orchestrator import RESEARCH_ORCHESTRATOR_AGENT_NAME

from .graph import build_research_orchestrator_graph, run_research_orchestrator


def get_research_orchestrator_runner(runtime_name: str) -> Callable[..., Awaitable[dict]]:
    if runtime_name != RESEARCH_ORCHESTRATOR_AGENT_NAME:
        raise ValueError(f"Unknown agent runtime: {runtime_name}")
    return run_research_orchestrator


__all__ = ["build_research_orchestrator_graph", "get_research_orchestrator_runner", "run_research_orchestrator"]
