from datetime import datetime, timedelta, timezone

import httpx
from jose import jwt

from app.config import settings
from app.models.user import User
from app.repositories.user_repository import UserRepository

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def build_google_auth_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


async def exchange_code_for_user_info(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo_resp.raise_for_status()
        return userinfo_resp.json()


async def get_or_create_user(user_info: dict, repo: UserRepository) -> User:
    provider_user_id = user_info["sub"]
    email = user_info["email"]
    display_name = user_info.get("name", email.split("@")[0])
    avatar_url = user_info.get("picture")

    user = await repo.get_by_oauth("google", provider_user_id)
    if user:
        return user

    # Existing account via email (different OAuth provider or manual)
    existing = await repo.get_by_email(email)
    if existing:
        return existing

    return await repo.create(
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
        provider="google",
        provider_user_id=provider_user_id,
    )


def create_jwt(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expire_minutes
    )
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "display_name": user.display_name,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
