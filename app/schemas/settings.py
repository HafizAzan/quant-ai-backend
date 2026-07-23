from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProfileOut(BaseModel):
    full_name: str
    email: str
    avatar_initials: str


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120)


class SecurityOut(BaseModel):
    two_factor_enabled: bool
    session_timeout: str
    two_factor_pending: bool = False


class SecurityUpdateRequest(BaseModel):
    session_timeout: str | None = Field(default=None, pattern="^(15|30|60|240)$")
    two_factor_enabled: bool | None = None


class TwoFactorEnrollOut(BaseModel):
    secret: str
    otpauth_url: str
    qr_payload: str


class TwoFactorVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str
    key_prefix: str
    permission: str
    created_at: datetime


class ApiKeyCreateRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=120)
    permission: str = Field(default="read-only", pattern="^(read-write|read-only)$")


class ApiKeyCreatedOut(BaseModel):
    key: ApiKeyOut
    secret: str


class AiModelOut(BaseModel):
    primary_engine: str
    temperature: float
    autonomous_execution: bool


class AiModelUpdateRequest(BaseModel):
    primary_engine: str | None = Field(
        default=None,
        pattern="^(gpt-4o-finance|gpt-4o|claude-sonnet|gemini-pro)$",
    )
    temperature: float | None = Field(default=None, ge=0, le=1)
    autonomous_execution: bool | None = None


class RiskOut(BaseModel):
    max_drawdown_daily: str
    max_position_size: str
    max_leverage: str
    critical_stop_enabled: bool
    critical_stop_drawdown_pct: str


class RiskUpdateRequest(BaseModel):
    max_drawdown_daily: str | None = Field(default=None, max_length=32)
    max_position_size: str | None = Field(default=None, max_length=32)
    max_leverage: str | None = Field(default=None, max_length=32)
    critical_stop_enabled: bool | None = None
    critical_stop_drawdown_pct: str | None = Field(default=None, max_length=32)


class SettingsStateOut(BaseModel):
    profile: ProfileOut
    security: SecurityOut
    api_keys: list[ApiKeyOut]
    ai_model: AiModelOut
    risk: RiskOut
