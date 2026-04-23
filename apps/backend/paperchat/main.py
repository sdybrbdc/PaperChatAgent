from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse

from paperchat.api.errcode import AppError
from paperchat.api.router import router
from paperchat.database.sql import init_database
from paperchat.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.server.name,
        version=settings.server.version,
        description=(
            "PaperChatAgent 后端 API。"
            "当前版本仅保留认证与聊天模块，主聊天与右侧专业提示区通过两条独立链路驱动。"
        ),
        docs_url="/swagger",
        openapi_url="/openapi.json",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "Auth", "description": "登录、登出、刷新与恢复登录态"},
            {"name": "Conversations", "description": "会话列表、消息流、动态专业提示与研究草案"},
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": getattr(request.state, "request_id", ""),
            },
        )

    @app.get("/health")
    async def healthcheck():
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/swagger")

    @app.on_event("startup")
    async def startup() -> None:
        init_database()

    app.include_router(router)
    return app


app = create_app()
