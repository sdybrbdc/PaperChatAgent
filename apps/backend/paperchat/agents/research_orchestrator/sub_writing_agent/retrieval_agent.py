from __future__ import annotations

from typing import Any

from paperchat.agents.research_orchestrator.runtime_support import summarize_text


async def run_retrieval(
    *,
    user_request: str,
    sections: list[str],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    global_analysis = str((analysis.get("global_analysis") or {}).get("global_analyse") or "")
    return {
        "missing_tools": ["knowledge_base_retrieval"],
        "skipped_capabilities": ["knowledge_base_retrieval"],
        "retrieved_docs": [],
        "context_summary": summarize_text(global_analysis or user_request, limit=1200),
        "sections": sections,
    }
