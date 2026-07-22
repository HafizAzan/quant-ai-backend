from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    safe_decode_token,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import (
    EmailVerificationRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    TokenPair,
    UserPublic,
)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.email_verifications = EmailVerificationRepository(session)

    async def register(self, payload: RegisterRequest) -> AuthResponse:
        if not payload.accept_terms:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Terms must be accepted")

        existing = await self.users.get_by_email(payload.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        user = await self.users.create(
            email=payload.email,
            full_name=payload.full_name.strip(),
            hashed_password=hash_password(payload.password),
        )
        await self._issue_email_verification(user)
        tokens = await self._issue_tokens(user)
        return AuthResponse(user=UserPublic.model_validate(user), tokens=tokens)

    async def login(self, payload: LoginRequest) -> AuthResponse:
        user = await self.users.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

        tokens = await self._issue_tokens(user)
        return AuthResponse(user=UserPublic.model_validate(user), tokens=tokens)

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = safe_decode_token(refresh_token)
        if payload is None or payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        jti = payload.get("jti")
        user_id = payload.get("sub")
        if not jti or not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        stored = await self.refresh_tokens.get_by_jti(jti)
        if stored is None or stored.revoked_at is not None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
        if stored.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
        if stored.token_hash != self._hash_token(refresh_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user = await self.users.get_by_id(UUID(user_id))
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        await self.refresh_tokens.revoke(stored)
        return await self._issue_tokens(user)

    async def logout(self, refresh_token: str | None) -> MessageResponse:
        if refresh_token:
            payload = safe_decode_token(refresh_token)
            if payload and payload.get("type") == "refresh" and payload.get("jti"):
                stored = await self.refresh_tokens.get_by_jti(payload["jti"])
                if stored and stored.revoked_at is None:
                    await self.refresh_tokens.revoke(stored)
        return MessageResponse(message="Signed out")

    async def logout_all(self, user_id: UUID) -> MessageResponse:
        await self.refresh_tokens.revoke_all_for_user(user_id)
        return MessageResponse(message="All sessions signed out")

    async def verify_email(self, token: str) -> MessageResponse:
        token_hash = self._hash_token(token)
        row = await self.email_verifications.get_by_token_hash(token_hash)
        if row is None or row.consumed_at is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")
        if row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification token expired")

        user = await self.users.get_by_id(row.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        await self.users.mark_email_verified(user)
        await self.email_verifications.consume(row)
        return MessageResponse(message="Email verified")

    async def resend_verification(self, email: str) -> MessageResponse:
        user = await self.users.get_by_email(email)
        # Always return success to avoid email enumeration
        if user and not user.is_email_verified:
            await self._issue_email_verification(user)
        return MessageResponse(message="If the account exists, a verification email was sent")

    async def get_me(self, user_id: UUID) -> UserPublic:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserPublic.model_validate(user)

    async def _issue_tokens(self, user: User) -> TokenPair:
        jti = uuid4().hex
        access = create_access_token(user.id, user.email)
        # Embed jti in refresh token via extra claim by re-encoding
        from datetime import datetime as dt
        from jose import jwt

        now = dt.now(timezone.utc)
        refresh_payload = {
            "sub": str(user.id),
            "type": "refresh",
            "jti": jti,
            "iat": now,
            "exp": now + timedelta(days=settings.refresh_token_expire_days),
        }
        refresh = jwt.encode(refresh_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

        await self.refresh_tokens.create(
            user_id=user.id,
            jti=jti,
            token_hash=self._hash_token(refresh),
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )
        return TokenPair(access_token=access, refresh_token=refresh)

    async def _issue_email_verification(self, user: User) -> str:
        raw = token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        await self.email_verifications.create(
            user_id=user.id,
            token_hash=self._hash_token(raw),
            expires_at=expires_at,
        )
        # Email delivery will be wired later; token available for verify endpoint in logs/dev
        if settings.debug:
            print(f"[DEV] Email verification token for {user.email}: {raw}")
        return raw

    @staticmethod
    def _hash_token(token: str) -> str:
        return sha256(token.encode("utf-8")).hexdigest()
