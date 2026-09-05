"""API v1 router — aggregates feature-module routers under /api/v1."""
from fastapi import APIRouter

from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router

router = APIRouter(prefix=settings.API_V1_STR)

router.include_router(auth_router)
router.include_router(users_router)