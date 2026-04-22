from fastapi import APIRouter

from paperchat.api.v1 import agents, auth, conversations, knowledge, tasks, workspaces


api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(conversations.router)
api_v1_router.include_router(tasks.router)
api_v1_router.include_router(workspaces.router)
api_v1_router.include_router(knowledge.router)
api_v1_router.include_router(agents.router)
