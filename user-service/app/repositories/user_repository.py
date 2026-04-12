import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.oauth_account import OAuthAccount


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_oauth(self, provider: str, provider_user_id: str) -> User | None:
        result = await self.db.execute(
            select(User)
            .join(OAuthAccount, OAuthAccount.user_id == User.id)
            .where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[User]:
        result = await self.db.execute(select(User).order_by(User.created_at))
        return list(result.scalars().all())

    async def create(
        self,
        email: str,
        display_name: str,
        avatar_url: str | None,
        provider: str,
        provider_user_id: str,
        role: str = "player",
    ) -> User:
        user = User(
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()  # get user.id before linking oauth

        oauth = OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
        )
        self.db.add(oauth)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_role(self, user: User, role: str) -> User:
        user.role = role
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.commit()
