from __future__ import annotations

from typing import Any

from fastapi import Request
from pydantic import BaseModel


class APIResponse(BaseModel):
    code: str
    message: str
    data: Any = None
    request_id: str


def request_id_from(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def ok(request: Request, data: Any = None, message: str = "success") -> APIResponse:
    return APIResponse(code="OK", message=message, data=data, request_id=request_id_from(request))
