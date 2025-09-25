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
from .app_routes import get_authenticated_user



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
        oauth_data = await WhoopIntegration.initiate_whoop_oauth(db, current_user.user_id)
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
        result = await WhoopIntegration.whoop_callback(db, code, state, error)
        
        # Always redirect to mobile app
        # return RedirectResponse(url=result["redirect_url"])
        return result
        
    except Exception as e:
        print(f"❌ Unexpected error in OAuth callback: {str(e)}")
        error_url = "fitpro://callback?error=unexpected_error&message=Unexpected error occurred"
        return RedirectResponse(url=error_url)

@whoop_router.get("/status")
async def get_whoop_connection_status(
    current_user = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if user has Whoop connected and get basic info"""
    try:
        # Check if user has Whoop linked
        if not current_user.whoop_user_id:
            return {
                "connected": False,
                "message": "Whoop account not linked"
            }
        
        return {
            "connected": True,
            "whoop_user_id": current_user.whoop_user_id,
            "message": "Whoop account linked"
        }    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check status: {str(e)}")
    
@whoop_router.get("/profile")
async def whoop_user_profile(
    db: AsyncSession = Depends(get_db), 
    current_user = Depends(get_authenticated_user)
):
    try:
        result = await WhoopIntegration.get_user_profile(db, current_user.user_id)

        return result
    except Exception as e:
        print(f"❌ Unexpected error in OAuth callback: {str(e)}")
        error_url = "fitpro://callback?error=unexpected_error&message=Unexpected error occurred"
        return RedirectResponse(url=error_url)
    
@whoop_router.get("/recovery")
async def get_whoop_recovery(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_authenticated_user)
):
    try:
        result = await WhoopIntegration.get_recovery_data(db, current_user.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recovery data: {str(e)}")

@whoop_router.get("/workouts")
async def get_whoop_workouts(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_authenticated_user)
):
    try:
        result = await WhoopIntegration.get_workout_data(db, current_user.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workout data: {str(e)}")

@whoop_router.get("/sleep")
async def get_whoop_sleep(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_authenticated_user)
):
    try:
        result = await WhoopIntegration.get_sleep_data(db, current_user.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sleep data: {str(e)}")