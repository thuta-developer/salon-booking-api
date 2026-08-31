from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.core.token_blacklist import revoke_token

from app.api.deps import get_db, get_current_active_user, oauth2_scheme
from app.schemas.token import Token, LoginRequest, RefreshTokenRequest
from app.schemas.user import UserCreate, UserResponse
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    service = UserService(UserRepository(db))
    return await service.register_user(user_in)


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
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

    service = UserService(UserRepository(db))
    return await service.login_user(login_data.email, login_data.password)


@router.post("/refresh", response_model=dict, status_code=status.HTTP_200_OK)
async def refresh_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    service = UserService(UserRepository(db))
    return await service.refresh_access_token(body.refresh_token)


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user


@router.post("/logout", status_code=status.HTTP_200_OK)
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
