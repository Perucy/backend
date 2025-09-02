from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import requests
import secrets
import hashlib
import base64
import os
from dotenv import load_dotenv
from urllib.parse import urlencode
from typing import Optional

from databases.database import get_db, User
from databases.db_service import store_oauth_token, get_oauth_token
from integrations.whoop import WhoopIntegration
from auth_routes import get_authenticated_user



load_dotenv()

whoop_router = APIRouter()

@whoop_router.get("/auth/login")
async def initiate_whoop_login(
    current_user = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start Whoop OAuth flow for authenticated FitPro user
    Requires JWT token to identify which FitPro user is linking
    """
    try:
        oauth_data = await WhoopIntegration.initiate_oauth(db, current_user.user_id)
        return oauth_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate Whoop OAuth: {str(e)}")

@whoop_router.get("/auth/callback")
async def whoop_auth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None, 
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Whoop OAuth callback
    Redirects to mobile app with success/error status
    """
    try:
        result = await WhoopIntegration.handle_oauth_callback(db, code, state, error)
        
        # Always redirect to mobile app
        return RedirectResponse(url=result["redirect_url"])
        
    except Exception as e:
        print(f"❌ Unexpected error in OAuth callback: {str(e)}")
        error_url = "fitpro://callback?error=unexpected_error&message=Unexpected error occurred"
        return RedirectResponse(url=error_url)