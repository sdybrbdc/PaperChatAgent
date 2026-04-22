from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from paperchat.api.responses import APIResponse, ok
from paperchat.auth import get_current_user


router = APIRouter(prefix="/agents", tags=["Agents"])


WORKFLOW_ID = "paperchat-default-workflow"
WORKFLOW_NODES = [
    {
        "id": "search_agent_node",
        "title": "搜索节点",
        "description": "收束需求并构建检索条件",
        "status": "idle",
        "order": 1,
    },
    {
        "id": "reading_agent_node",
        "title": "阅读节点",
        "description": "解析论文摘要与全文结构",
        "status": "idle",
        "order": 2,
    },
    {
        "id": "analyse_agent_node",
        "title": "分析节点",
        "description": "聚类并形成主题分析",
        "status": "idle",
        "order": 3,
    },
    {
        "id": "writing_agent_node",
        "title": "写作节点",
        "description": "整理阶段性写作结果",
        "status": "idle",
        "order": 4,
    },
    {
        "id": "report_agent_node",
        "title": "报告节点",
        "description": "生成主题探索包与最终产物",
        "status": "idle",
        "order": 5,
    },
]


@router.get("/workflows", response_model=APIResponse)
async def list_workflows(request: Request, user=Depends(get_current_user)):
    return ok(
        request,
        data={
            "items": [
                {
                    "id": WORKFLOW_ID,
                    "name": "PaperChatAgent 默认研究工作流",
                    "node_count": len(WORKFLOW_NODES),
                }
            ]
        },
    )


@router.get("/workflows/{workflow_id}", response_model=APIResponse)
async def get_workflow(workflow_id: str, request: Request, user=Depends(get_current_user)):
    return ok(
        request,
        data={
            "id": workflow_id,
            "name": "PaperChatAgent 默认研究工作流",
            "node_count": len(WORKFLOW_NODES),
            "description": "当前为占位工作流定义，用于前后端联调与 Swagger 展示。",
        },
    )


@router.get("/workflows/{workflow_id}/nodes", response_model=APIResponse)
async def get_workflow_nodes(workflow_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data={"items": WORKFLOW_NODES})
