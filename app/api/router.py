"""API v1 router — aggregates feature-module routers under /api/v1."""
from fastapi import APIRouter

from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.shop.router import router as shops_router
from app.modules.shop.router import owner_router as shops_owner_router
from app.modules.shop.router import admin_router as shops_admin_router
from app.modules.shop_barbers.router import router as barbers_router
from app.modules.categories.router import public_router as categories_router
from app.modules.categories.router import owner_router as categories_owner_router

router = APIRouter(prefix=settings.API_V1_STR)

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(shops_router)
router.include_router(shops_owner_router)
router.include_router(shops_admin_router)
router.include_router(barbers_router)
router.include_router(categories_router)
router.include_router(categories_owner_router)