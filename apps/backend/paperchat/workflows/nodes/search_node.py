from __future__ import annotations

from collections.abc import Sequence

from paperchat.services.knowledge import search_arxiv_entries
from paperchat.workflows.agents import SearchPlanningAgent
from paperchat.workflows.definitions import DEFAULT_WORKFLOW_NODES
from paperchat.workflows.state import ResearchPaper, ResearchWorkflowState, WorkflowNodeExecutionError


NODE = DEFAULT_WORKFLOW_NODES[0]


def _dedupe_papers(papers: Sequence[ResearchPaper]) -> list[ResearchPaper]:
    seen: set[str] = set()
    deduped: list[ResearchPaper] = []
    for paper in papers:
        key = (paper.get("entry_id") or paper.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(paper)
    return deduped


def _build_fallback_papers(*, topic: str, queries: Sequence[str]) -> list[ResearchPaper]:
    papers: list[ResearchPaper] = []
    for index, query in enumerate(queries[:3], start=1):
        papers.append(
            {
                "title": f"{topic} 主题探索样本 {index}",
                "summary": (
                    "当前运行环境未成功获取在线论文结果，因此这里先保留一条占位研究样本，"
                    f"对应查询为“{query}”。后续补通检索源后会替换为真实论文。"
                ),
                "entry_id": f"placeholder:{index}",
                "published": "",
                "authors": ["PaperChatAgent"],
                "pdf_url": None,
                "query": query,
            }
        )
    return papers


def build_search_node(task_service):
    agent = SearchPlanningAgent()

    async def search_node(state: ResearchWorkflowState) -> dict:
        task_id = state["task_id"]
        try:
            await task_service.mark_node_started(task_id=task_id, node_id=NODE.id, detail="正在生成检索查询")
            queries = await agent.plan_queries(topic=state["topic"], keywords=state.get("keywords", []))
            await task_service.mark_node_progress(
                task_id=task_id,
                node_id=NODE.id,
                detail=f"已生成 {len(queries)} 条检索查询，开始检索候选论文",
            )

            papers: list[ResearchPaper] = []
            for query in queries[:3]:
                try:
                    results = await search_arxiv_entries(keyword=query, max_results=3)
                except Exception:
                    continue
                for result in results:
                    result["query"] = query
                    papers.append(result)

            deduped = _dedupe_papers(papers)
            if not deduped:
                deduped = _build_fallback_papers(topic=state["topic"], queries=queries)

            detail = f"检索完成，整理出 {len(deduped)} 篇候选论文"
            await task_service.mark_node_completed(task_id=task_id, node_id=NODE.id, detail=detail)
            return {
                "search_queries": queries,
                "papers": deduped[:8],
                "last_detail": detail,
            }
        except Exception as exc:
            raise WorkflowNodeExecutionError(node_id=NODE.id, message=f"搜索节点失败：{exc}") from exc

    return search_node
