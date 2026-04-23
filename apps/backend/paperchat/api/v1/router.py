from fastapi import APIRouter

from paperchat.api.v1 import auth, conversations


api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(conversations.router)
