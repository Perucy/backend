from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from databases.database import get_db
from auth.auth import (
    register_user, 
    refresh_access_token, 
    login_user,
    get_current_user
)

router = APIRouter()
security = HTTPBearer()

class UserRegistration(BaseModel):
    email: str
    password: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/register")
async def register(user_data: UserRegistration, db: AsyncSession = Depends(get_db)):
    try:
        result = await register_user(db, user_data.email, user_data.password, user_data.first_name, user_data.last_name, user_data.username)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/login")
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        result = await login_user(db, login_data.email, login_data.password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/refresh")
async def refresh_token_endpoint(token_request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await refresh_access_token(db, token_request.refresh_token)
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.get("/me")
async def get_current_user_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's profile info
    Protected endpoint - requires valid JWT token
    """
    try:
        token = credentials.credentials
        current_user = await get_current_user(db, token)
        
        return {
            "user_id": current_user.user_id,
            "email": current_user.email,
            "username": current_user.username,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "display_name": current_user.display_name or current_user.first_name or current_user.username,
            "created_at": current_user.created_at,
            "linked_accounts": {
                "whoop": current_user.whoop_user_id is not None,
                "spotify": current_user.spotify_user_id is not None
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))   
    
# ============================================================================
# HELPER DEPENDENCY FOR OTHER ROUTERS
# ============================================================================

async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Dependency function that other routers can use
    Returns the authenticated user object
    """
    try:
        token = credentials.credentials
        user = await get_current_user(db, token)
        return user
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Authentication required")
__all__ = ["router", "get_authenticated_user"]