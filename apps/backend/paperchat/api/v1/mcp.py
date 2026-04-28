from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from paperchat.api.responses import APIResponse, ok
from paperchat.auth import get_current_user
from paperchat.schemas.mcp import McpServiceCreate, McpServiceUpdate, McpToolCallRequest
from paperchat.services.mcp import mcp_service


router = APIRouter(prefix="/mcp", tags=["MCP"])


@router.get("/services", response_model=APIResponse)
async def list_mcp_services(request: Request, user=Depends(get_current_user)):
    return ok(request, data=mcp_service.list_services_payload(user.id))


@router.get("/sources/cc-switch", response_model=APIResponse)
async def list_cc_switch_mcp_services(request: Request, user=Depends(get_current_user)):
    return ok(request, data=mcp_service.list_cc_switch_services_payload())


@router.post("/sync/cc-switch", response_model=APIResponse)
async def sync_cc_switch_mcp_services(request: Request, user=Depends(get_current_user)):
    return ok(request, data=await mcp_service.sync_cc_switch_services_payload(user.id))


@router.post("/services", response_model=APIResponse)
async def create_mcp_service(payload: McpServiceCreate, request: Request, user=Depends(get_current_user)):
    return ok(request, data=mcp_service.create_service_payload(user.id, payload))


@router.get("/services/{service_id}", response_model=APIResponse)
async def get_mcp_service(service_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=mcp_service.get_service_payload(user.id, service_id))


@router.patch("/services/{service_id}", response_model=APIResponse)
async def update_mcp_service(
    service_id: str,
    payload: McpServiceUpdate,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(request, data=mcp_service.update_service_payload(user.id, service_id, payload))


@router.delete("/services/{service_id}", response_model=APIResponse)
async def delete_mcp_service(service_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=mcp_service.delete_service_payload(user.id, service_id))


@router.post("/services/{service_id}/test", response_model=APIResponse)
async def test_mcp_service(service_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=await mcp_service.test_service_payload(user.id, service_id))


@router.post("/services/{service_id}/refresh-tools", response_model=APIResponse)
async def refresh_mcp_tools(service_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=await mcp_service.refresh_tools_payload(user.id, service_id))


@router.get("/tools", response_model=APIResponse)
async def list_mcp_tools(request: Request, user=Depends(get_current_user)):
    return ok(request, data=mcp_service.list_tools_payload(user.id))


@router.post("/services/{service_id}/tools/{tool_name}/call", response_model=APIResponse)
async def call_mcp_tool(
    service_id: str,
    tool_name: str,
    payload: McpToolCallRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(
        request,
        data=await mcp_service.call_tool_payload(
            user_id=user.id,
            service_id=service_id,
            tool_name=tool_name,
            arguments=payload.arguments,
        ),
    )
