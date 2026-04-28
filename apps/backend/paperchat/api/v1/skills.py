from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from paperchat.api.responses import APIResponse, ok
from paperchat.auth import get_current_user
from paperchat.schemas.skills import (
    SkillCreate,
    SkillFileAddRequest,
    SkillFileDeleteRequest,
    SkillFileUpdateRequest,
    SkillImportRequest,
    SkillTestRequest,
    SkillUpdate,
)
from paperchat.services.skills import skill_service


router = APIRouter(prefix="/skills", tags=["Skills"])


@router.get("", response_model=APIResponse)
async def list_skills(request: Request, user=Depends(get_current_user)):
    return ok(request, data=skill_service.list_skills_payload(user.id))


@router.get("/sources/cc-switch", response_model=APIResponse)
async def list_cc_switch_skills(request: Request, user=Depends(get_current_user)):
    return ok(request, data=skill_service.list_cc_switch_skills_payload())


@router.post("/sync/cc-switch", response_model=APIResponse)
async def sync_cc_switch_skills(request: Request, user=Depends(get_current_user)):
    return ok(request, data=skill_service.sync_cc_switch_skills_payload(user.id))


@router.post("", response_model=APIResponse)
async def create_skill(payload: SkillCreate, request: Request, user=Depends(get_current_user)):
    return ok(request, data=skill_service.create_skill_payload(user.id, payload))


@router.post("/import", response_model=APIResponse)
async def import_skill(payload: SkillImportRequest, request: Request, user=Depends(get_current_user)):
    return ok(request, data=skill_service.import_skill_payload(user.id, payload))


@router.post("/import-local", response_model=APIResponse)
async def import_local_skill(payload: SkillImportRequest, request: Request, user=Depends(get_current_user)):
    return ok(request, data=skill_service.import_skill_payload(user.id, payload))


@router.post("/{skill_id}/files", response_model=APIResponse)
async def add_skill_file(
    skill_id: str,
    payload: SkillFileAddRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(request, data=skill_service.add_skill_file_payload(user_id=user.id, skill_id=skill_id, payload=payload))


@router.patch("/{skill_id}/files", response_model=APIResponse)
async def update_skill_file(
    skill_id: str,
    payload: SkillFileUpdateRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(request, data=skill_service.update_skill_file_payload(user_id=user.id, skill_id=skill_id, payload=payload))


@router.delete("/{skill_id}/files", response_model=APIResponse)
async def delete_skill_file(
    skill_id: str,
    payload: SkillFileDeleteRequest,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(request, data=skill_service.delete_skill_file_payload(user_id=user.id, skill_id=skill_id, payload=payload))


@router.get("/{skill_id}", response_model=APIResponse)
async def get_skill(skill_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=skill_service.get_skill_payload(user.id, skill_id))


@router.patch("/{skill_id}", response_model=APIResponse)
async def update_skill(
    skill_id: str,
    payload: SkillUpdate,
    request: Request,
    user=Depends(get_current_user),
):
    return ok(request, data=skill_service.update_skill_payload(user.id, skill_id, payload))


@router.delete("/{skill_id}", response_model=APIResponse)
async def delete_skill(skill_id: str, request: Request, user=Depends(get_current_user)):
    return ok(request, data=skill_service.delete_skill_payload(user.id, skill_id))


@router.post("/{skill_id}/test", response_model=APIResponse)
async def test_skill(skill_id: str, payload: SkillTestRequest, request: Request, user=Depends(get_current_user)):
    return ok(request, data=skill_service.test_skill_payload(user.id, skill_id, payload))
