from fastapi import APIRouter
from app.core.config import settings
from app.api.v1.endpoints import (
    auth,
    users,
    permissions,
    roles,
)




router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(roles.router)
router.include_router(permissions.router)

