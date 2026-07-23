from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.settings import (
    AiModelOut,
    AiModelUpdateRequest,
    ApiKeyCreatedOut,
    ApiKeyCreateRequest,
    ProfileOut,
    ProfileUpdateRequest,
    RiskOut,
    RiskUpdateRequest,
    SecurityOut,
    SecurityUpdateRequest,
    SettingsStateOut,
    TwoFactorEnrollOut,
    TwoFactorVerifyRequest,
)
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["Settings"])


def get_settings_service(session: AsyncSession = Depends(get_db)) -> SettingsService:
    return SettingsService(session)


@router.get("", response_model=APIResponse[SettingsStateOut])
async def get_settings(
    current_user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
) -> APIResponse[SettingsStateOut]:
    return APIResponse(data=await service.get_state(current_user))


@router.patch("/profile", response_model=APIResponse[ProfileOut])
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
) -> APIResponse[ProfileOut]:
    return APIResponse(message="Profile updated", data=await service.update_profile(current_user, payload))


@router.patch("/security", response_model=APIResponse[SecurityOut])
async def update_security(
    payload: SecurityUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
) -> APIResponse[SecurityOut]:
    return APIResponse(message="Security updated", data=await service.update_security(current_user.id, payload))


@router.post("/security/2fa/enroll", response_model=APIResponse[TwoFactorEnrollOut])
async def enroll_2fa(
    current_user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
) -> APIResponse[TwoFactorEnrollOut]:
    return APIResponse(message="Scan QR / enter secret, then verify", data=await service.enroll_2fa(current_user))


@router.post("/security/2fa/verify", response_model=APIResponse[SecurityOut])
async def verify_2fa(
    payload: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
) -> APIResponse[SecurityOut]:
    return APIResponse(message="2FA enabled", data=await service.verify_2fa(current_user.id, payload))


@router.post("/api-keys", response_model=APIResponse[ApiKeyCreatedOut])
async def create_api_key(
    payload: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
) -> APIResponse[ApiKeyCreatedOut]:
    return APIResponse(message="API key created — copy secret now", data=await service.create_api_key(current_user.id, payload))


@router.delete("/api-keys/{key_id}", response_model=APIResponse[None])
async def delete_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
) -> APIResponse[None]:
    await service.delete_api_key(current_user.id, key_id)
    return APIResponse(message="API key revoked", data=None)


@router.patch("/ai-model", response_model=APIResponse[AiModelOut])
async def update_ai_model(
    payload: AiModelUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
) -> APIResponse[AiModelOut]:
    return APIResponse(message="AI preferences updated", data=await service.update_ai(current_user.id, payload))


@router.patch("/risk", response_model=APIResponse[RiskOut])
async def update_risk(
    payload: RiskUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: SettingsService = Depends(get_settings_service),
) -> APIResponse[RiskOut]:
    return APIResponse(message="Risk limits updated", data=await service.update_risk(current_user.id, payload))
