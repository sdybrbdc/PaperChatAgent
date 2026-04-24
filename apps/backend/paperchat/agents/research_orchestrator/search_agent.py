from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import arxiv
from pydantic import BaseModel, Field

from paperchat.agents.research_orchestrator.runtime_support import (
    call_autogen_agent,
    extract_json_object,
)
from paperchat.agents.research_orchestrator.state_models import ExecutionState, PaperAgentState
from paperchat.prompts.research_orchestrator import SEARCH_AGENT_PROMPT


class SearchQuery(BaseModel):
    queries: list[str] = Field(default_factory=list)
    rationale: str = ""
    start_date: str | None = None
    end_date: str | None = None


def _format_arxiv_date(value: str | None, *, fallback: str) -> str:
    if not value:
        return fallback
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y-%m", "%Y/%m", "%Y"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%Y%m%d0000")
        except ValueError:
            continue
    return fallback


def _paper_to_dict(result: arxiv.Result) -> dict[str, Any]:
    return {
        "paper_id": result.get_short_id(),
        "title": result.title,
        "authors": [author.name for author in result.authors],
        "summary": result.summary,
        "published": result.published.year if result.published else None,
        "published_date": result.published.isoformat() if result.published else None,
        "url": result.entry_id,
        "pdf_url": result.pdf_url,
        "primary_category": result.primary_category,
        "categories": result.categories,
        "doi": result.doi if hasattr(result, "doi") else None,
    }


def _build_arxiv_query(query: SearchQuery) -> str:
    terms = [item.strip() for item in query.queries if item and item.strip()]
    if not terms:
        return ""
    search_query = " OR ".join(f'all:"{term}"' for term in terms)
    if query.start_date or query.end_date:
        start = _format_arxiv_date(query.start_date, fallback="190001010000")
        end = _format_arxiv_date(query.end_date, fallback=datetime.now().strftime("%Y%m%d2359"))
        search_query = f"({search_query}) AND submittedDate:[{start} TO {end}]"
    return search_query


async def _generate_search_query(state: PaperAgentState, *, model_slot: str) -> SearchQuery:
    response = await call_autogen_agent(
        name="search_agent",
        system_prompt=SEARCH_AGENT_PROMPT,
        user_prompt=f"用户研究需求：{state.user_request}\n最大论文数：{state.max_papers}",
        model_slot=model_slot,
    )
    try:
        data = extract_json_object(response)
        if "querys" in data and "queries" not in data:
            data["queries"] = data["querys"]
        query = SearchQuery.model_validate(data)
    except Exception:
        query = SearchQuery(queries=[state.user_request], rationale="fallback to raw user request")
    if not query.queries:
        query.queries = [state.user_request]
    return query


async def _search_arxiv(query: SearchQuery, *, max_results: int) -> list[dict[str, Any]]:
    arxiv_query = _build_arxiv_query(query)
    if not arxiv_query:
        return []

    def _run() -> list[dict[str, Any]]:
        search = arxiv.Search(
            query=arxiv_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
            sort_order=arxiv.SortOrder.Descending,
        )
        return [_paper_to_dict(item) for item in search.results()]

    return await asyncio.to_thread(_run)


async def search_node(state: PaperAgentState, *, model_slot: str = "conversation_model") -> dict[str, Any]:
    state.current_step = ExecutionState.SEARCHING
    query = await _generate_search_query(state, model_slot=model_slot)
    papers = await _search_arxiv(query, max_results=state.max_papers)
    state.search_queries = query.queries
    state.search_results = papers
    if not papers:
        state.error.search_node_error = "没有找到相关论文，请尝试更换研究主题或扩大范围"
    return {
        "detail": f"论文搜索完成，共找到 {len(papers)} 篇论文",
        "output": {
            "queries": query.queries,
            "rationale": query.rationale,
            "papers": papers,
        },
    }
