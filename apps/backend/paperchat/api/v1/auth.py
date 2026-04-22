from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, EmailStr, Field

from paperchat.api.errcode import AppError
from paperchat.api.responses import APIResponse, ok
from paperchat.auth.service import (
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    refresh_session,
    set_auth_cookies,
    verify_password,
)
from paperchat.database.dao import memory_store
from paperchat.settings import AppSettings, get_settings


router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", response_model=APIResponse)
async def register(payload: RegisterRequest, request: Request):
    if memory_store.get_user_by_email(payload.email):
        raise AppError(status_code=409, code="AUTH_INVALID_CREDENTIALS", message="邮箱已注册")

    user = memory_store.create_user(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    inbox, session = memory_store.create_default_inbox(user.id)
    return ok(
        request,
        data={
            "user_id": user.id,
            "inbox_conversation_id": inbox.id,
            "default_session_id": session.id,
        },
    )


@router.post("/login", response_model=APIResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    settings: AppSettings = Depends(get_settings),
):
    user = memory_store.get_user_by_email(payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError(status_code=401, code="AUTH_INVALID_CREDENTIALS", message="邮箱或密码错误")

    access_placeholder = "pending"
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.auth.refresh_token_ttl_seconds)
    session = memory_store.create_user_session(user_id=user.id, refresh_token=access_placeholder, expires_at=expires_at)
    access_token = create_access_token(user.id, session.id, settings)
    refresh_token = create_refresh_token(user.id, session.id, settings)
    memory_store.update_refresh_token(session.id, refresh_token, expires_at)
    set_auth_cookies(response, access_token, refresh_token, settings)
    return ok(request, data={"user": memory_store.as_user_payload(user)})


@router.post("/refresh", response_model=APIResponse)
async def refresh(
    request: Request,
    response: Response,
    settings: AppSettings = Depends(get_settings),
):
    _user, _session, access_token, refresh_token = refresh_session(request, settings)
    set_auth_cookies(response, access_token, refresh_token, settings)
    return ok(request, data={"refreshed": True})


@router.post("/logout", response_model=APIResponse)
async def logout(
    request: Request,
    response: Response,
    settings: AppSettings = Depends(get_settings),
):
    refresh_cookie = request.cookies.get(settings.auth.refresh_cookie_name)
    if refresh_cookie:
        try:
            payload = jwt.decode(refresh_cookie, settings.auth.secret_key, algorithms=["HS256"])
            session_id = payload.get("sid")
            if session_id:
                memory_store.revoke_user_session(session_id)
        except Exception:
            pass
    clear_auth_cookies(response, settings)
    return ok(request, data={"logged_out": True})


@router.get("/me", response_model=APIResponse)
async def me(request: Request, user=Depends(get_current_user)):
    return ok(request, data=memory_store.as_user_payload(user))
