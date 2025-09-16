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
from integrations.spotify import SpotifyIntegration
from .app_routes import get_authenticated_user

load_dotenv()

spotify_router = APIRouter()

@spotify_router.get("/auth/login")
async def initiate_spotify_login(
    current_user = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        oauth_data = await SpotifyIntegration.initiate_spotify_oauth(db, current_user.user_id)
        return oauth_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate Spotify OAuth: {str(e)}")
      

@spotify_router.get("/auth/callback")
async def spotify_callback(
    code: Optional[str] = None,  # ← Make code optional
    state: Optional[str] = None,  # ← Make state optional  
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Whoop OAuth callback
    Redirects to mobile app with success/error status
    """
    try:
        result = await SpotifyIntegration.spotify_callback(db, code, state, error)
        
        # Always redirect to mobile app
        # return RedirectResponse(url=result["redirect_url"])
        return result
    except Exception as e:
        print(f"❌ Unexpected error in OAuth callback: {str(e)}")
        error_url = "fitpro://callback?error=unexpected_error&message=Unexpected error occurred"
        return RedirectResponse(url=error_url)
    
def get_user_access_token(user_id: str) -> str:
    """Get access token for user"""
    if user_id not in user_tokens:
        raise HTTPException(status_code=401, detail="User not authenticated")
    return user_tokens[user_id]['access_token']

async def make_spotify_request(user_id: str, endpoint: str, params: dict = None):
    """Make authenticated request to Spotify API"""
    access_token = get_user_access_token(user_id)
    
    headers = {
        'Authorization': f"Bearer {access_token}",
        'Content-Type': 'application/json'
    }
    
    url = f"{SPOTIFY_API_BASE}/{endpoint.lstrip('/')}"
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 401:
            # Token might be expired
            raise HTTPException(status_code=401, detail="Access token expired. Please re-authenticate.")
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Spotify API error: {response.text}"
            )
        
        return response.json()
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Spotify: {str(e)}")

@spotify_router.get("/api/user/{user_id}/profile")
async def get_user_profile(user_id: str):
    """Get user's Spotify profile"""
    return await make_spotify_request(user_id, "/me")

@spotify_router.get("/api/user/{user_id}/playlists")
async def get_user_playlists(user_id: str, limit: int = 20, offset: int = 0):
    """Get user's playlists"""
    params = {'limit': limit, 'offset': offset}
    return await make_spotify_request(user_id, "/me/playlists", params)

@spotify_router.get("/api/user/{user_id}/playlist/{playlist_id}")
async def get_playlist_details(user_id: str, playlist_id: str):
    """Get details of a specific playlist"""
    return await make_spotify_request(user_id, f"/playlists/{playlist_id}")

@spotify_router.get("/api/user/{user_id}/playlist/{playlist_id}/tracks")
async def get_playlist_tracks(user_id: str, playlist_id: str, limit: int = 50, offset: int = 0):
    """Get tracks from a specific playlist"""
    params = {'limit': limit, 'offset': offset}
    return await make_spotify_request(user_id, f"/playlists/{playlist_id}/tracks", params)

@spotify_router.get("/api/user/{user_id}/top-tracks")
async def get_user_top_tracks(user_id: str, time_range: str = "medium_term", limit: int = 20):
    """Get user's top tracks"""
    params = {'time_range': time_range, 'limit': limit}
    return await make_spotify_request(user_id, "/me/top/tracks", params)

@spotify_router.get("/api/user/{user_id}/top-artists")
async def get_user_top_artists(user_id: str, time_range: str = "medium_term", limit: int = 20):
    """Get user's top artists"""
    params = {'time_range': time_range, 'limit': limit}
    return await make_spotify_request(user_id, "/me/top/artists", params)

@spotify_router.get("/api/user/{user_id}/recently-played")
async def get_recently_played(user_id: str, limit: int = 20):
    """Get user's recently played tracks"""
    params = {'limit': limit}
    return await make_spotify_request(user_id, "/me/player/recently-played", params)

@spotify_router.delete("/api/user/{user_id}/disconnect")
async def disconnect_user(user_id: str):
    """Disconnect user from Spotify"""
    if user_id in user_tokens:
        del user_tokens[user_id]
        return {"message": "Successfully disconnected from Spotify"}
    else:
        raise HTTPException(status_code=404, detail="User not found")

@spotify_router.get("/api/user/{user_id}/status")
async def get_user_status(user_id: str):
    """Check if user is still authenticated"""
    if user_id in user_tokens:
        profile = user_tokens[user_id]['profile']
        return {
            "authenticated": True,
            "user_id": user_id,
            "display_name": profile.get('display_name'),
            "email": profile.get('email')
        }
    else:
        raise HTTPException(status_code=404, detail="User not authenticated")