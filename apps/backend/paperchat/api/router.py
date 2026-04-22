from fastapi import APIRouter

from paperchat.api.v1.router import api_v1_router


router = APIRouter(prefix="/api")
router.include_router(api_v1_router)
