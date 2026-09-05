"""Auth module API routes — authentication + RBAC (roles/permissions) management."""
import uuid
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Query,
    Request,
    status,
)

from app.common.dependencies import (
    get_current_active_user,
    has_permission,
    oauth2_scheme,
)
from app.common.pagination import PaginatedResponse
from app.core.security import decode_token
from app.core.token_blacklist import revoke_token
from app.modules.auth.dependencies import (
    get_auth_service,
    get_permission_service,
    get_role_service,
)
from app.modules.auth.schemas import (
    LoginRequest,
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
    RefreshTokenRequest,
    RoleAssignPermissions,
    RoleCreate,
    RoleResponse,
    Token,
    UserAssignRoles,
)
from app.modules.auth.service import PermissionService, RoleService
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserResponse

router = APIRouter()

# ------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_in: UserCreate,
    service=Depends(get_auth_service),
):
    return await service.register_user(user_in)


@auth_router.post("/login", response_model=Token)
async def login(
    request: Request,
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    service=Depends(get_auth_service),
):
    if username is not None and password is not None:
        login_data = LoginRequest(email=username, password=password)
    else:
        try:
            login_data = LoginRequest.model_validate(await request.json())
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Login requires JSON {email, password} or form fields username and password",
            )

    client_ip = request.client.host if request.client else None
    return await service.login_user(
        login_data.email, login_data.password, client_ip=client_ip
    )


@auth_router.post("/refresh", response_model=Token, status_code=status.HTTP_200_OK)
async def refresh_token(
    body: RefreshTokenRequest,
    service=Depends(get_auth_service),
):
    refresh_result = await service.refresh_access_token(body.refresh_token)
    return Token(**refresh_result)


@auth_router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user


@auth_router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: Annotated[User, Depends(get_current_active_user)],
    token: str = Depends(oauth2_scheme),
):
    payload = decode_token(token)
    if not payload or not await revoke_token(payload):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to revoke this token",
        )

    return {
        "message": f"User '{current_user.email}' successfully logged out",
        "detail": "Token revoked. Please discard stored tokens on the client side.",
    }


# ------------------------------------------------------------------
# Roles management (RBAC)
# ------------------------------------------------------------------
roles_router = APIRouter(prefix="/roles", tags=["Roles Management"])


@roles_router.post(
    "/",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("role:create"))],
)
async def create_role(
    role_in: RoleCreate,
    service: RoleService = Depends(get_role_service),
):
    return await service.create_role(role_in)


@roles_router.get(
    "/",
    response_model=PaginatedResponse[RoleResponse],
    dependencies=[Depends(has_permission("role:read"))],
)
async def list_roles(
    search: Optional[str] = Query(None, description="Search name or description"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    service: RoleService = Depends(get_role_service),
):
    return await service.get_roles_list(search=search, page=page, size=size)


@roles_router.get(
    "/{role_id}",
    response_model=RoleResponse,
    dependencies=[Depends(has_permission("role:read"))],
)
async def get_role_by_id(
    role_id: uuid.UUID,
    service: RoleService = Depends(get_role_service),
):
    return await service.get_role_by_id(role_id=role_id)


@roles_router.post(
    "/{role_id}/permissions",
    response_model=RoleResponse,
    dependencies=[Depends(has_permission("role:update"))],
)
async def assign_permissions_to_role(
    role_id: uuid.UUID,
    data: RoleAssignPermissions,
    service: RoleService = Depends(get_role_service),
):
    return await service.assign_permissions_to_role(role_id, data)


@roles_router.post(
    "/users/{user_id}/assign-roles",
    response_model=UserResponse,
    dependencies=[Depends(has_permission("user:update"))],
)
async def assign_roles_to_user(
    user_id: uuid.UUID,
    body: UserAssignRoles,
    current_user: User = Depends(has_permission("user:update")),
    service: RoleService = Depends(get_role_service),
):
    return await service.assign_roles_to_user(
        user_id, body.role_ids, acting_user=current_user
    )


@roles_router.delete(
    "/{role_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("role:delete"))],
)
async def delete_role(
    role_id: uuid.UUID,
    service: RoleService = Depends(get_role_service),
):
    return await service.delete_role(role_id)


# ------------------------------------------------------------------
# Permissions management (RBAC)
# ------------------------------------------------------------------
permissions_router = APIRouter(prefix="/permissions", tags=["Permissions Management"])


@permissions_router.post(
    "/",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("permission:create"))],
)
async def create_permission(
    perm_in: PermissionCreate,
    service: PermissionService = Depends(get_permission_service),
):
    return await service.create_permission(perm_in)


@permissions_router.get(
    "/",
    response_model=PaginatedResponse[PermissionResponse],
    dependencies=[Depends(has_permission("permission:read"))],
)
async def list_permissions(
    search: Optional[str] = Query(None, description="Search name or description"),
    module: Optional[str] = Query(None, description="Filter by module e.g., 'Bus'"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    service: PermissionService = Depends(get_permission_service),
):
    return await service.get_permissions_list(
        search=search, module=module, page=page, size=size
    )


@permissions_router.put(
    "/{perm_id}",
    response_model=PermissionResponse,
    dependencies=[Depends(has_permission("permission:update"))],
)
async def update_permission(
    perm_id: uuid.UUID,
    perm_in: PermissionUpdate,
    service: PermissionService = Depends(get_permission_service),
):
    return await service.update_permission(perm_id, perm_in)


@permissions_router.delete(
    "/{perm_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("permission:delete"))],
)
async def delete_permission(
    perm_id: uuid.UUID,
    service: PermissionService = Depends(get_permission_service),
):
    return await service.delete_permission(perm_id)


# ------------------------------------------------------------------
# Module aggregator — mounted under /api/v1 by app/api/router.py
# ------------------------------------------------------------------
router.include_router(auth_router)
router.include_router(roles_router)
router.include_router(permissions_router)