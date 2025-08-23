from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import requests
import secrets
import hashlib
import base64
import os
from dotenv import load_dotenv
from urllib.parse import urlencode
from typing import Optional
import json

load_dotenv()

app = FastAPI(title="Spotify Integration Backend")

# CORS for React Native
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Spotify config
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

# Spotify API URLs
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

# Simple in-memory storage
user_tokens = {}
auth_states = {}

def generate_code_verifier():
    """Generate PKCE code verifier"""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

def generate_code_challenge(verifier: str):
    """Generate PKCE code challenge"""
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')

@app.get("/")
async def root():
    return {"message": "Spotify Backend is running!", "version": "1.0.0"}

@app.get("/auth/login")
async def initiate_spotify_login():
    """Start Spotify OAuth flow with PKCE"""
    # Generate PKCE parameters
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(32)
    
    # Store for later verification
    auth_states[state] = {
        'code_verifier': code_verifier,
        'created_at': secrets.token_hex(16)  # Simple timestamp substitute
    }
    
    # Build authorization URL
    auth_params = {
        'client_id': SPOTIFY_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'scope': 'user-read-private user-read-email playlist-read-private playlist-read-collaborative user-library-read user-top-read',
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
        'state': state,
        'show_dialog': 'true'  # Always show login dialog
    }
    
    auth_url = f"{SPOTIFY_AUTH_URL}?{urlencode(auth_params)}"
    
    return {
        "auth_url": auth_url,
        "state": state
    }

@app.get("/auth/callback")
async def spotify_callback(code: str, state: str, error: Optional[str] = None):
    """Handle Spotify OAuth callback"""
    if error:
        raise HTTPException(status_code=400, detail=f"Spotify authorization error: {error}")
    
    # Verify state and get code verifier
    if state not in auth_states:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")
    
    code_verifier = auth_states[state]['code_verifier']
    del auth_states[state]  # Clean up
    
    # Exchange authorization code for access token
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'client_id': SPOTIFY_CLIENT_ID,
        'code_verifier': code_verifier
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        # Get access token
        token_response = requests.post(SPOTIFY_TOKEN_URL, data=token_data, headers=headers)
        
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=400, 
                detail=f"Token exchange failed: {token_response.text}"
            )
        
        token_info = token_response.json()
        access_token = token_info['access_token']
        
        # Get user profile
        profile_response = requests.get(
            f"{SPOTIFY_API_BASE}/me",
            headers={'Authorization': f"Bearer {access_token}"}
        )
        
        if profile_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to fetch user profile: {profile_response.text}"
            )
        
        user_profile = profile_response.json()
        user_id = user_profile['id']
        
        # Store user tokens and profile
        user_tokens[user_id] = {
            'access_token': access_token,
            'refresh_token': token_info.get('refresh_token'),
            'expires_in': token_info.get('expires_in'),
            'profile': user_profile
        }
        
        return {
            "success": True,
            "user_id": user_id,
            "user_info": user_profile,
            "message": "Successfully connected to Spotify!"
        }
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

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

@app.get("/api/user/{user_id}/profile")
async def get_user_profile(user_id: str):
    """Get user's Spotify profile"""
    return await make_spotify_request(user_id, "/me")

@app.get("/api/user/{user_id}/playlists")
async def get_user_playlists(user_id: str, limit: int = 20, offset: int = 0):
    """Get user's playlists"""
    params = {'limit': limit, 'offset': offset}
    return await make_spotify_request(user_id, "/me/playlists", params)

@app.get("/api/user/{user_id}/playlist/{playlist_id}")
async def get_playlist_details(user_id: str, playlist_id: str):
    """Get details of a specific playlist"""
    return await make_spotify_request(user_id, f"/playlists/{playlist_id}")

@app.get("/api/user/{user_id}/playlist/{playlist_id}/tracks")
async def get_playlist_tracks(user_id: str, playlist_id: str, limit: int = 50, offset: int = 0):
    """Get tracks from a specific playlist"""
    params = {'limit': limit, 'offset': offset}
    return await make_spotify_request(user_id, f"/playlists/{playlist_id}/tracks", params)

@app.get("/api/user/{user_id}/top-tracks")
async def get_user_top_tracks(user_id: str, time_range: str = "medium_term", limit: int = 20):
    """Get user's top tracks"""
    params = {'time_range': time_range, 'limit': limit}
    return await make_spotify_request(user_id, "/me/top/tracks", params)

@app.get("/api/user/{user_id}/top-artists")
async def get_user_top_artists(user_id: str, time_range: str = "medium_term", limit: int = 20):
    """Get user's top artists"""
    params = {'time_range': time_range, 'limit': limit}
    return await make_spotify_request(user_id, "/me/top/artists", params)

@app.get("/api/user/{user_id}/recently-played")
async def get_recently_played(user_id: str, limit: int = 20):
    """Get user's recently played tracks"""
    params = {'limit': limit}
    return await make_spotify_request(user_id, "/me/player/recently-played", params)

@app.delete("/api/user/{user_id}/disconnect")
async def disconnect_user(user_id: str):
    """Disconnect user from Spotify"""
    if user_id in user_tokens:
        del user_tokens[user_id]
        return {"message": "Successfully disconnected from Spotify"}
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.get("/api/user/{user_id}/status")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
