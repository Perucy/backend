from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from urllib.parse import urlencode,quote
from typing import Optional, Dict, Any
from dotenv import load_dotenv

import requests
import secrets
import hashlib
import base64
import os

from databases.database import get_db, User, OAuthToken
from databases.db_service import store_oauth_token, get_oauth_token
from databases.oauth_state_service import OAuthStateService

load_dotenv()

# Spotify config
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

# Spotify API URLs
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"

class SpotifyIntegration:
    @staticmethod
    def generate_code_verifier():
        """Generate PKCE code verifier"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

    @staticmethod
    def generate_code_challenge(verifier: str):
        """Generate PKCE code challenge"""
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
    
    @staticmethod
    async def initiate_spotify_oauth(db: AsyncSession, fitpro_user_id: str) -> Dict[str, str]:
        code_verifier = SpotifyIntegration.generate_code_verifier()
        code_challenge = SpotifyIntegration.generate_code_challenge(code_verifier)
        state = secrets.token_urlsafe(32) #placeholder

        success = await OAuthStateService.store_state(
            db=db,
            state=state,
            provider_name='spotify',
            fitpro_user_id=fitpro_user_id,
            code_verifier=code_verifier,
            expires_in_minutes=10
        )

        if not success:
            raise ValueError("Failed to store OAuth state")

        auth_params = {
            'client_id': SPOTIFY_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': SPOTIFY_REDIRECT_URI,
            'scope': 'user-read-private user-read-email playlist-read-private playlist-read-collaborative user-library-read user-top-read',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'state': state,  # Fixed: Added missing state parameter
            'show_dialog': 'true'
        }

        auth_url = f"{SPOTIFY_AUTH_URL}?{urlencode(auth_params)}"

        return {
            "auth_url": auth_url,
            "state": state
        }
    
    @staticmethod
    async def spotify_callback(
        db: AsyncSession,
        code: Optional[str] = None,  # ← Make code optional
        state: Optional[str] = None,  # ← Make state optional  
        error: Optional[str] = None
    ):
        """Handle Spotify OAuth callback"""
        
        # Handle user cancellation first
        if error == "access_denied":
            return {
                "success": False,
                "error": "user_cancelled",
                "redirect_url": "fitpro://callback?cancelled=true&message=Authentication cancelled by user"
            }
        
        # Handle other errors
        if error:
            return {
                "success": False,
                "error": error,
                "redirect_url": f"fitpro://callback?error={error}&message=Authentication failed"
            }
        
        # Now check for required parameters (only needed for successful flow)
        if not code or not state:
            return {
                "success": False,
                "error": "missing parameters",
                "redirect_url": f"fitpro://callback?error=missing_parameter&message=missing required parameters"
            }
        
        state_data = await OAuthStateService.get_and_delete_state(db, state, "spotify")
        print("😂 State data:", state_data)
        if not state_data:
            return {
                "success": False,
                "error": "invalid_state",
                "redirect_url": "fitpro://callback?error=invalid_state&message=Invalid or expired request"
            }
        
        fitpro_user_id = state_data['fitpro_user_id']
        code_verifier = state_data['code_verifier']
        
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

            # Get access token
            print(f"🔄 Exchanging code for access token...")
            token_response = requests.post(SPOTIFY_TOKEN_URL, data=token_data, headers=headers)
            
            if token_response.status_code != 200:
                print(f"❌ Spotify Token exchange failed: {token_response.status_code} - {token_response.text}")
                return {
                    "success": False,
                    "error": "token_exchange_failed",
                    "redirect_url": "fitpro://callback?error=token_exchange_failed&message=Failed to exchange authorization code"
                }
            
            token_info = token_response.json()
            access_token = token_info['access_token']
            
            # Get user profile
            print(f"🔄 Fetching user profile...")
            profile_response = requests.get(
                f"{SPOTIFY_API_BASE_URL}/me",
                headers={'Authorization': f"Bearer {access_token}"}
            )
            
            if profile_response.status_code != 200:
                print(f"❌ Profile fetch failed: {profile_response.status_code} - {profile_response.text}")
                return {
                    "success": False,
                    "error": "profile_fetch_failed",
                    "redirect_url": "fitpro://callback?error=profile_fetch_failed&message=Failed to retrieve Spotify user profile"
                }
            
            spotify_profile = profile_response.json()
            spotify_user_id = spotify_profile['id']

            fitpro_user = await db.get(User, fitpro_user_id)
            if fitpro_user:
                fitpro_user.spotify_user_id = spotify_user_id
            
            # Store user tokens and profile
            await store_oauth_token(
                db=db,
                user_id=fitpro_user_id,
                provider='spotify',
                access_token=access_token,
                refresh_token=token_info.get('refresh_token'),
                expires_in=token_info.get('expires_in')
            )
            
            
            display_name = spotify_profile.get('display_name', 'Spotify User')
            display_name_encoded = quote(display_name)
            success_url = f"fitpro://callback?success=true&user_id={fitpro_user_id}&display_name={display_name_encoded}"
            return {
                "success": True,
                "fitpro_user_id": fitpro_user_id,
                "spotify_user_id": spotify_user_id,
                "display_name": display_name,
                "redirect_url": success_url
            }
        
        except requests.RequestException as e:
            print(f"❌ Network error during Spotify token exchange: {str(e)}")
            return {
                "success": False,
                "error": "network_error",
                "redirect_url": "fitpro://callback?error=network_error&message=Network error during authentication"
            }
        except Exception as e:
            print(f"❌ Unexpected error during Spotify token exchange: {str(e)}")
            return {
                "success": False,
                "error": "unexpected_error",
                "redirect_url": "fitpro://callback?error=unexpected_error&message=Unexpected error occurred"
            }
        
    @staticmethod
    async def make_spotify_api_request(db: AsyncSession, fitpro_user_id: str, endpoint: str, params: dict = None) -> Optional[Dict[str, Any]]:
        """
        Make authenticated request to Spotify API
        
        Args:
            fitpro_user_id: FitPro user ID (not Spotify user ID)
            endpoint: API endpoint (e.g., "user/profile/basic")
            params: Query parameters
        """
        # Get stored OAuth token
        token_data = await get_oauth_token(db, fitpro_user_id, 'Spotify')
        if not token_data:
            raise ValueError("User not authenticated with Spotify")
        
        headers = {
            'Authorization': f"Bearer {token_data['access_token']}",
            'Content-Type': 'application/json'
        }
        
        url = f"{SPOTIFY_API_BASE_URL}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 401:
                raise ValueError("Access token expired. Please re-authenticate.")
            
            if response.status_code != 200:
                raise ValueError(f"Spotify API error: {response.text}")
            
            return response.json()
            
        except requests.RequestException as e:
            raise ValueError(f"Failed to connect to Spotify: {str(e)}")

    @staticmethod   
    async def get_user_profile(user_id: str):
        """Get user's Spotify profile"""
        return await SpotifyIntegration.make_spotify_api_request(user_id, "/me")

    @staticmethod
    async def get_user_playlists(user_id: str, limit: int = 20, offset: int = 0):
        """Get user's playlists"""
        params = {'limit': limit, 'offset': offset}
        return await SpotifyIntegration.make_spotify_api_request(user_id, "/me/playlists", params)