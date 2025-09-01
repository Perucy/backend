from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
import requests
import secrets
import hashlib
import base64
import os
from dotenv import load_dotenv
from urllib.parse import urlencode
from typing import Optional

load_dotenv()

spotify_router = APIRouter()

# Spotify config
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

# Spotify API URLs
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

user_tokens = {}
auth_states = {}

def generate_code_verifier():
    """Generate PKCE code verifier"""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

def generate_code_challenge(verifier: str):
    """Generate PKCE code challenge"""
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')

@spotify_router.get("/auth/login")
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

@spotify_router.get("/auth/callback")
async def spotify_callback(
    code: Optional[str] = None,  # ← Make code optional
    state: Optional[str] = None,  # ← Make state optional  
    error: Optional[str] = None
):
    """Handle Spotify OAuth callback"""
    
    # Handle user cancellation first
    if error == "access_denied":
        print(f"🚫 User cancelled OAuth flow")
        cancel_url = "fitpro://callback?cancelled=true&message=Authentication cancelled by user"
        return RedirectResponse(url=cancel_url)
    
    # Handle other errors
    if error:
        print(f"❌ OAuth error: {error}")
        error_url = f"fitpro://callback?error={error}&message=Authentication failed"
        return RedirectResponse(url=error_url)
    
    # Now check for required parameters (only needed for successful flow)
    if not code:
        print(f"❌ No authorization code received")
        error_url = "fitpro://callback?error=no_code&message=No authorization code received"
        return RedirectResponse(url=error_url)
        
    if not state:
        print(f"❌ No state parameter received")
        error_url = "fitpro://callback?error=no_state&message=No state parameter received"
        return RedirectResponse(url=error_url)
    
    # Verify state and get code verifier
    if state not in auth_states:
        print(f"❌ Invalid or expired state parameter: {state}")
        error_url = "fitpro://callback?error=invalid_state&message=Invalid or expired request"
        return RedirectResponse(url=error_url)
    
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
        print(f"🔄 Exchanging code for access token...")
        token_response = requests.post(SPOTIFY_TOKEN_URL, data=token_data, headers=headers)
        
        if token_response.status_code != 200:
            print(f"❌ Token exchange failed: {token_response.status_code} - {token_response.text}")
            error_url = "fitpro://callback?error=token_exchange_failed&message=Failed to exchange authorization code"
            return RedirectResponse(url=error_url)
        
        token_info = token_response.json()
        access_token = token_info['access_token']
        
        # Get user profile
        print(f"🔄 Fetching user profile...")
        profile_response = requests.get(
            f"{SPOTIFY_API_BASE}/me",
            headers={'Authorization': f"Bearer {access_token}"}
        )
        
        if profile_response.status_code != 200:
            print(f"❌ Profile fetch failed: {profile_response.status_code} - {profile_response.text}")
            error_url = "fitpro://callback?error=profile_fetch_failed&message=Failed to retrieve user profile"
            return RedirectResponse(url=error_url)
        
        user_profile = profile_response.json()
        user_id = user_profile['id']
        
        # Store user tokens and profile
        user_tokens[user_id] = {
            'access_token': access_token,
            'refresh_token': token_info.get('refresh_token'),
            'expires_in': token_info.get('expires_in'),
            'profile': user_profile
        }
        
        print(f"✅ OAuth successful for user: {user_profile.get('display_name')} ({user_id})")
        
        # Redirect to mobile spotify_router with success
        from urllib.parse import quote
        display_name = quote(user_profile.get('display_name', ''))
        success_url = f"fitpro://callback?success=true&user_id={user_id}&display_name={display_name}"
        return RedirectResponse(url=success_url)
    
    except requests.RequestException as e:
        print(f"❌ Network error during token exchange: {str(e)}")
        error_url = "fitpro://callback?error=network_error&message=Network error during authentication"
        return RedirectResponse(url=error_url)
    except Exception as e:
        print(f"❌ Unexpected error during token exchange: {str(e)}")
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