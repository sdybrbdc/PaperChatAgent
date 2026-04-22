from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256

import jwt
from fastapi import Depends, Request, Response

from paperchat.api.errcode import AppError
from paperchat.database.dao import memory_store
from paperchat.settings import AppSettings, get_settings


def hash_password(password: str) -> str:
    return sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _cookie_kwargs(settings: AppSettings) -> dict:
    return {
        "httponly": True,
        "secure": settings.auth.cookie_secure,
        "samesite": settings.auth.cookie_samesite,
        "path": "/",
    }


def _encode_token(*, user_id: str, session_id: str, token_type: str, ttl_seconds: int, settings: AppSettings) -> str:
    payload = {
        "sub": user_id,
        "sid": session_id,
        "type": token_type,
        "iat": int(_utcnow().timestamp()),
        "exp": int((_utcnow() + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.auth.secret_key, algorithm="HS256")


def _decode_token(token: str, expected_type: str, settings: AppSettings) -> dict:
    try:
        payload = jwt.decode(token, settings.auth.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AppError(
            status_code=401,
            code="AUTH_SESSION_EXPIRED",
            message="登录会话已失效，请重新登录",
        ) from exc
    if payload.get("type") != expected_type:
        raise AppError(
            status_code=401,
            code="AUTH_SESSION_EXPIRED",
            message="登录会话已失效，请重新登录",
        )
    return payload


def create_access_token(user_id: str, session_id: str, settings: AppSettings) -> str:
    return _encode_token(
        user_id=user_id,
        session_id=session_id,
        token_type="access",
        ttl_seconds=settings.auth.access_token_ttl_seconds,
        settings=settings,
    )


def create_refresh_token(user_id: str, session_id: str, settings: AppSettings) -> str:
    return _encode_token(
        user_id=user_id,
        session_id=session_id,
        token_type="refresh",
        ttl_seconds=settings.auth.refresh_token_ttl_seconds,
        settings=settings,
    )


def set_auth_cookies(response: Response, access_token: str, refresh_token: str, settings: AppSettings) -> None:
    cookie_kwargs = _cookie_kwargs(settings)
    response.set_cookie(
        settings.auth.access_cookie_name,
        access_token,
        max_age=settings.auth.access_token_ttl_seconds,
        **cookie_kwargs,
    )
    response.set_cookie(
        settings.auth.refresh_cookie_name,
        refresh_token,
        max_age=settings.auth.refresh_token_ttl_seconds,
        **cookie_kwargs,
    )


def clear_auth_cookies(response: Response, settings: AppSettings) -> None:
    response.delete_cookie(settings.auth.access_cookie_name, path="/")
    response.delete_cookie(settings.auth.refresh_cookie_name, path="/")


def _token_from_request(request: Request, settings: AppSettings, expected_type: str) -> str | None:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()

    cookie_name = (
        settings.auth.access_cookie_name if expected_type == "access" else settings.auth.refresh_cookie_name
    )
    return request.cookies.get(cookie_name)


def _resolve_user_from_token(request: Request, expected_type: str, settings: AppSettings):
    token = _token_from_request(request, settings, expected_type)
    if not token:
        raise AppError(status_code=401, code="AUTH_SESSION_EXPIRED", message="请先登录")

    payload = _decode_token(token, expected_type, settings)
    session = memory_store.get_user_session(payload["sid"])
    if session is None or session.revoked_at is not None:
        raise AppError(status_code=401, code="AUTH_SESSION_EXPIRED", message="登录会话已失效，请重新登录")
    user = memory_store.get_user(payload["sub"])
    if user is None:
        raise AppError(status_code=401, code="AUTH_SESSION_EXPIRED", message="登录会话已失效，请重新登录")
    return user, session, token


def get_current_user(request: Request, settings: AppSettings = Depends(get_settings)):
    user, _session, _token = _resolve_user_from_token(request, "access", settings)
    return user


def get_optional_current_user(request: Request, settings: AppSettings = Depends(get_settings)):
    token = _token_from_request(request, settings, "access")
    if not token:
        return None
    try:
        user, _session, _token = _resolve_user_from_token(request, "access", settings)
        return user
    except AppError:
        return None


def refresh_session(request: Request, settings: AppSettings) -> tuple:
    user, session, refresh_token = _resolve_user_from_token(request, "refresh", settings)
    if session.refresh_token_hash != sha256(refresh_token.encode("utf-8")).hexdigest():
        raise AppError(status_code=401, code="AUTH_SESSION_EXPIRED", message="登录会话已失效，请重新登录")

    access_token = create_access_token(user.id, session.id, settings)
    new_refresh_token = create_refresh_token(user.id, session.id, settings)
    expires_at = _utcnow() + timedelta(seconds=settings.auth.refresh_token_ttl_seconds)
    memory_store.update_refresh_token(session.id, new_refresh_token, expires_at)
    return user, session, access_token, new_refresh_token
