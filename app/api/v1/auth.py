from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_auth_service, get_current_user
from app.models.user import User
from app.schemas.auth import (
    APIResponse,
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    TokenPair,
    UserPublic,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=APIResponse[AuthResponse], status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> APIResponse[AuthResponse]:
    data = await service.register(payload)
    return APIResponse(message="Account created", data=data)


@router.post("/login", response_model=APIResponse[AuthResponse])
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> APIResponse[AuthResponse]:
    data = await service.login(payload)
    return APIResponse(message="Signed in", data=data)


@router.post("/refresh", response_model=APIResponse[TokenPair])
async def refresh(
    payload: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> APIResponse[TokenPair]:
    data = await service.refresh(payload.refresh_token)
    return APIResponse(message="Token refreshed", data=data)


@router.post("/logout", response_model=APIResponse[MessageResponse])
async def logout(
    payload: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> APIResponse[MessageResponse]:
    data = await service.logout(payload.refresh_token)
    return APIResponse(data=data)


@router.post("/verify-email", response_model=APIResponse[MessageResponse])
async def verify_email(
    payload: VerifyEmailRequest,
    service: AuthService = Depends(get_auth_service),
) -> APIResponse[MessageResponse]:
    data = await service.verify_email(payload.token)
    return APIResponse(data=data)


@router.post("/resend-verification", response_model=APIResponse[MessageResponse])
async def resend_verification(
    payload: ResendVerificationRequest,
    service: AuthService = Depends(get_auth_service),
) -> APIResponse[MessageResponse]:
    data = await service.resend_verification(payload.email)
    return APIResponse(data=data)


@router.get("/me", response_model=APIResponse[UserPublic])
async def me(current_user: User = Depends(get_current_user)) -> APIResponse[UserPublic]:
    return APIResponse(data=UserPublic.model_validate(current_user))
