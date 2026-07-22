from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import EmailVerification, RefreshToken, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        full_name: str,
        hashed_password: str,
    ) -> User:
        user = User(
            email=email.lower(),
            full_name=full_name,
            hashed_password=hashed_password,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def mark_email_verified(self, user: User) -> User:
        user.is_email_verified = True
        await self.session.flush()
        return user


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: UUID,
        jti: str,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        row = RefreshToken(
            user_id=user_id,
            jti=jti,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        result = await self.session.execute(select(RefreshToken).where(RefreshToken.jti == jti))
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        now = datetime.now(timezone.utc)
        for token in result.scalars().all():
            token.revoked_at = now
        await self.session.flush()


class EmailVerificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> EmailVerification:
        row = EmailVerification(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_by_token_hash(self, token_hash: str) -> EmailVerification | None:
        result = await self.session.execute(
            select(EmailVerification).where(EmailVerification.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def consume(self, row: EmailVerification) -> None:
        row.consumed_at = datetime.now(timezone.utc)
        await self.session.flush()
