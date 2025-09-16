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
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

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