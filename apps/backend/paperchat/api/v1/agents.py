from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from paperchat.api.responses import APIResponse, ok
from paperchat.auth import get_current_user
from paperchat.services.agents import agent_service


router = APIRouter(prefix="/agents", tags=["Agents"])


class SaveNodeConfigRequest(BaseModel):
    executor_key: str = ""
    fallback_executor_key: str = ""
    model_slot: str = "conversation_model"
    config: dict = Field(default_factory=dict)


class CreateAgentRunRequest(BaseModel):
    topic: str = Field(min_length=1)
    conversation_id: str | None = None
    max_papers: int = Field(default=6, ge=1, le=20)


@router.get("/workflows", response_model=APIResponse)
async def list_workflows(request: Request, user=Depends(get_current_user)):
    return ok(request, data=agent_service.list_workflows_payload(user.id))


@router.get("/workflows/{workflow_id}", response_model=APIResponse)
async def get_workflow(workflow_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=agent_service.get_workflow_payload(user_id=user.id, workflow_id=workflow_id))


@router.get("/workflows/{workflow_id}/nodes", response_model=APIResponse)
async def get_workflow_nodes(
    workflow_id: str,
    request: Request,
    run_id: str | None = Query(default=None),
    user=Depends(get_current_user),
):
    return ok(request, data=agent_service.get_nodes_payload(user_id=user.id, workflow_id=workflow_id, run_id=run_id))


@router.put("/workflows/{workflow_id}/nodes/{node_id}/config", response_model=APIResponse)
async def save_node_config(
    workflow_id: str,
    node_id: str,
    payload: SaveNodeConfigRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=agent_service.save_node_config_payload(
            user_id=user.id,
            workflow_id=workflow_id,
            node_id=node_id,
            executor_key=payload.executor_key,
            fallback_executor_key=payload.fallback_executor_key,
            model_slot=payload.model_slot,
            config=payload.config,
        ),
    )


@router.post("/workflows/{workflow_id}/runs", response_model=APIResponse)
async def create_workflow_run(
    workflow_id: str,
    payload: CreateAgentRunRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=await agent_service.create_run_payload(
            user_id=user.id,
            workflow_id=workflow_id,
            topic=payload.topic,
            conversation_id=payload.conversation_id,
            max_papers=payload.max_papers,
        ),
    )


@router.get("/runs/{run_id}", response_model=APIResponse)
async def get_run(run_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=agent_service.get_run_payload(user_id=user.id, run_id=run_id))


@router.get("/runs/{run_id}/nodes", response_model=APIResponse)
async def get_run_nodes(run_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=agent_service.get_run_nodes_payload(user_id=user.id, run_id=run_id))
