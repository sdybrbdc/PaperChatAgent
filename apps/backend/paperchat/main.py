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
            "聊天流由 LangChain / LangGraph 产生，FastAPI 通过 SSE 对前端传输。"
        ),
        docs_url="/swagger",
        openapi_url="/openapi.json",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "Auth", "description": "登录、登出、刷新与恢复登录态"},
            {"name": "Conversations", "description": "默认收件箱会话、消息列表与聊天流"},
            {"name": "Tasks", "description": "研究任务列表、详情、报告与进度流"},
            {"name": "Knowledge", "description": "知识库、文件上传与资料挂接"},
            {"name": "Agents", "description": "预置工作流与节点定义"},
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
