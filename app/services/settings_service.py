from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import UUID

import pyotp
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.settings import UserApiKey, UserSettings
from app.models.user import User
from app.repositories.settings_repository import SettingsRepository
from app.repositories.user_repository import UserRepository
from app.schemas.settings import (
    AiModelOut,
    AiModelUpdateRequest,
    ApiKeyCreatedOut,
    ApiKeyCreateRequest,
    ApiKeyOut,
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


def _initials(name: str) -> str:
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


class SettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SettingsRepository(session)
        self.users = UserRepository(session)

    async def ensure_settings(self, user_id: UUID) -> UserSettings:
        row = await self.repo.get_settings(user_id)
        if row is not None:
            return row
        row = UserSettings(user_id=user_id)
        return await self.repo.add_settings(row)

    async def get_state(self, user: User) -> SettingsStateOut:
        s = await self.ensure_settings(user.id)
        keys = await self.repo.list_api_keys(user.id)
        return SettingsStateOut(
            profile=ProfileOut(
                full_name=user.full_name,
                email=user.email,
                avatar_initials=_initials(user.full_name),
            ),
            security=SecurityOut(
                two_factor_enabled=s.two_factor_enabled,
                session_timeout=s.session_timeout,
                two_factor_pending=bool(s.two_factor_secret and not s.two_factor_enabled),
            ),
            api_keys=[ApiKeyOut.model_validate(k) for k in keys],
            ai_model=AiModelOut(
                primary_engine=s.primary_engine,
                temperature=s.temperature,
                autonomous_execution=s.autonomous_execution,
            ),
            risk=RiskOut(
                max_drawdown_daily=s.max_drawdown_daily,
                max_position_size=s.max_position_size,
                max_leverage=s.max_leverage,
                critical_stop_enabled=s.critical_stop_enabled,
                critical_stop_drawdown_pct=s.critical_stop_drawdown_pct,
            ),
        )

    async def update_profile(self, user: User, payload: ProfileUpdateRequest) -> ProfileOut:
        user.full_name = payload.full_name.strip()
        await self.session.flush()
        return ProfileOut(
            full_name=user.full_name,
            email=user.email,
            avatar_initials=_initials(user.full_name),
        )

    async def update_security(self, user_id: UUID, payload: SecurityUpdateRequest) -> SecurityOut:
        s = await self.ensure_settings(user_id)
        if payload.session_timeout is not None:
            s.session_timeout = payload.session_timeout
        if payload.two_factor_enabled is False:
            s.two_factor_enabled = False
            s.two_factor_secret = None
        await self.repo.flush()
        return SecurityOut(
            two_factor_enabled=s.two_factor_enabled,
            session_timeout=s.session_timeout,
            two_factor_pending=bool(s.two_factor_secret and not s.two_factor_enabled),
        )

    async def enroll_2fa(self, user: User) -> TwoFactorEnrollOut:
        s = await self.ensure_settings(user.id)
        secret = pyotp.random_base32()
        s.two_factor_secret = secret
        s.two_factor_enabled = False
        await self.repo.flush()
        totp = pyotp.TOTP(secret)
        url = totp.provisioning_uri(name=user.email, issuer_name="QuantAI")
        return TwoFactorEnrollOut(secret=secret, otpauth_url=url, qr_payload=url)

    async def verify_2fa(self, user_id: UUID, payload: TwoFactorVerifyRequest) -> SecurityOut:
        s = await self.ensure_settings(user_id)
        if not s.two_factor_secret:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA enrollment not started")
        if not pyotp.TOTP(s.two_factor_secret).verify(payload.code.strip(), valid_window=1):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid 2FA code")
        s.two_factor_enabled = True
        await self.repo.flush()
        return SecurityOut(
            two_factor_enabled=True,
            session_timeout=s.session_timeout,
            two_factor_pending=False,
        )

    async def create_api_key(self, user_id: UUID, payload: ApiKeyCreateRequest) -> ApiKeyCreatedOut:
        raw = f"ak_{secrets.token_urlsafe(32)}"
        prefix = raw[:12] + "..."
        row = UserApiKey(
            user_id=user_id,
            label=payload.label.strip(),
            key_prefix=prefix,
            key_hash=hash_password(raw),
            permission=payload.permission,
        )
        await self.repo.add_api_key(row)
        return ApiKeyCreatedOut(key=ApiKeyOut.model_validate(row), secret=raw)

    async def delete_api_key(self, user_id: UUID, key_id: UUID) -> None:
        row = await self.repo.get_api_key(user_id, key_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
        row.revoked_at = datetime.now(timezone.utc)
        await self.repo.flush()

    async def update_ai(self, user_id: UUID, payload: AiModelUpdateRequest) -> AiModelOut:
        s = await self.ensure_settings(user_id)
        if payload.primary_engine is not None:
            s.primary_engine = payload.primary_engine
        if payload.temperature is not None:
            s.temperature = payload.temperature
        if payload.autonomous_execution is not None:
            s.autonomous_execution = payload.autonomous_execution
        await self.repo.flush()
        return AiModelOut(
            primary_engine=s.primary_engine,
            temperature=s.temperature,
            autonomous_execution=s.autonomous_execution,
        )

    async def update_risk(self, user_id: UUID, payload: RiskUpdateRequest) -> RiskOut:
        s = await self.ensure_settings(user_id)
        if payload.max_drawdown_daily is not None:
            s.max_drawdown_daily = payload.max_drawdown_daily
        if payload.max_position_size is not None:
            s.max_position_size = payload.max_position_size
        if payload.max_leverage is not None:
            s.max_leverage = payload.max_leverage
        if payload.critical_stop_enabled is not None:
            s.critical_stop_enabled = payload.critical_stop_enabled
        if payload.critical_stop_drawdown_pct is not None:
            s.critical_stop_drawdown_pct = payload.critical_stop_drawdown_pct
        await self.repo.flush()
        return RiskOut(
            max_drawdown_daily=s.max_drawdown_daily,
            max_position_size=s.max_position_size,
            max_leverage=s.max_leverage,
            critical_stop_enabled=s.critical_stop_enabled,
            critical_stop_drawdown_pct=s.critical_stop_drawdown_pct,
        )
