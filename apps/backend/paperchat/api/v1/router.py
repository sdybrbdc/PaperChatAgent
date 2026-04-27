from fastapi import APIRouter

from paperchat.api.v1 import (
    agents,
    auth,
    capabilities,
    conversations,
    dashboard,
    knowledge,
    mcp,
    models,
    skills,
    tasks,
)


api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(conversations.router)
api_v1_router.include_router(agents.router)
api_v1_router.include_router(knowledge.router)
api_v1_router.include_router(mcp.router)
api_v1_router.include_router(skills.router)
api_v1_router.include_router(models.router)
api_v1_router.include_router(tasks.router)
api_v1_router.include_router(dashboard.router)
api_v1_router.include_router(capabilities.router)
