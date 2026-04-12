import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.services.auth_service import (
    build_google_auth_url,
    exchange_code_for_user_info,
    get_or_create_user,
    create_jwt,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google")
async def google_login():
    """Redirect user to Google OAuth consent screen."""
    state = secrets.token_urlsafe(16)
    url = build_google_auth_url(state)
    return RedirectResponse(url)


@router.get("/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback, upsert user, return JWT via redirect."""
    try:
        user_info = await exchange_code_for_user_info(code)
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to exchange OAuth code")

    repo = UserRepository(db)
    user = await get_or_create_user(user_info, repo)
    token = create_jwt(user)

    # Redirect to frontend with token in the URL fragment so it stays client-side
    return RedirectResponse(url=f"http://localhost/?token={token}")
