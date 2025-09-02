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

# Whoop config
WHOOP_CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
WHOOP_CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
WHOOP_REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI")

# whoop api urls
WHOOP_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_API_BASE_URL = "https://api.prod.whoop.com/developer/v2"

class WhoopIntegration:
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
    async def initiate_whoop_oauth(db: AsyncSession, fitpro_user_id: str) -> Dict[str, str]:
        code_verifier = WhoopIntegration.generate_code_verifier()
        code_challenge = WhoopIntegration.generate_code_challenge(code_verifier)
        state = secrets.token_urlsafe(32)

        success = await OAuthStateService.store_state(
            db=db,
            state=state,
            provider_name='whoop',
            fitpro_user_id=fitpro_user_id,
            code_verifier=code_verifier,
            expires_in_minutes=10
        )

        if not success:
            raise ValueError("Failed to store OAuth state")

        auth_params = {
            'client_id': WHOOP_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': WHOOP_REDIRECT_URI,
            'scope': 'offline read:profile read:recovery read:cycles read:sleep read:workout read:body_measurement',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'state': state,  # Fixed: Added missing state parameter
            'show_dialog': 'true'
        }

        auth_url = f"{WHOOP_AUTH_URL}?{urlencode(auth_params)}"

        return {
            "auth_url": auth_url,
            "state": state
        }
    
    @staticmethod
    async def handle_oauth_callback(db: AsyncSession, code: str, state: str, error: Optional[str] = None) -> Dict[str, Any]:
        if error == "access_denied":
            return {
                "success": False,
                "error": "user_cancelled",
                "redirect_url": "fitpro://callback?cancelled=true&message=Authentication cancelled by user"
            }
        
        if error:
            return {
                "success": False,
                "error": error,
                "redirect_url": f"fitpro://callback?error={error}&message=Authentication failed"
            }
        
        if not code or not state:
            return {
                "success": False,
                "error": "missing parameters",
                "redirect_url": f"fitpro://callback?error=missing_parameter&message=missing required parameters"
            }
        
        state_data = await OAuthStateService.get_and_delete_state(db, state, "whoop")
        if not state_data:
            return {
                "success": False,
                "error": "invalid_state",
                "redirect_url": "fitpro://callback?error=invalid_state&message=Invalid or expired request"
            }
        
        fitpro_user_id = state_data['fitpro_user_id']
        code_verifier = state_data['code_verifier']

        try:
            # Exchange code for tokens
            token_data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': WHOOP_REDIRECT_URI,
                'client_id': WHOOP_CLIENT_ID,
                'client_secret': WHOOP_CLIENT_SECRET,
                'code_verifier': code_verifier
            }
            
            token_response = requests.post(WHOOP_TOKEN_URL, data=token_data)
            
            if token_response.status_code != 200:
                print(f"❌ Token exchange failed: {token_response.status_code} - {token_response.text}")
                return {
                    "success": False,
                    "error": "token_exchange_failed",
                    "redirect_url": "fitpro://callback?error=token_exchange_failed&message=Failed to exchange authorization code"
                }
            
            tokens = token_response.json()
            access_token = tokens['access_token']
            
            # Get Whoop user profile
            profile_response = requests.get(
                f"{WHOOP_API_BASE_URL}/user/profile/basic",
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if profile_response.status_code != 200:
                print(f"❌ Profile fetch failed: {profile_response.status_code} - {profile_response.text}")
                return {
                    "success": False,
                    "error": "profile_fetch_failed",
                    "redirect_url": "fitpro://callback?error=profile_fetch_failed&message=Failed to retrieve user profile"
                }
            
            whoop_profile = profile_response.json()
            whoop_user_id = str(whoop_profile.get('user_id'))
            
            # Update FitPro user with Whoop user ID
            fitpro_user = await db.get(User, fitpro_user_id)
            if fitpro_user:
                fitpro_user.whoop_user_id = whoop_user_id
            
            # Store OAuth tokens
            await store_oauth_token(
                db=db,
                user_id=fitpro_user_id,  # FitPro user ID
                provider='whoop',
                access_token=access_token,
                refresh_token=tokens.get('refresh_token'),
                expires_in=tokens.get('expires_in')
            )
            
            display_name = whoop_profile.get('first_name', 'Whoop User')
            
            # Create success redirect URL
            display_name_encoded = quote(display_name)
            success_url = f"fitpro://callback?success=true&user_id={fitpro_user_id}&display_name={display_name_encoded}"

            return {
                "success": True,
                "fitpro_user_id": fitpro_user_id,
                "whoop_user_id": whoop_user_id,
                "display_name": display_name,
                "redirect_url": success_url
            }
            
        except requests.RequestException as e:
            print(f"❌ Network error during token exchange: {str(e)}")
            return {
                "success": False,
                "error": "network_error",
                "redirect_url": "fitpro://callback?error=network_error&message=Network error during authentication"
            }
        except Exception as e:
            print(f"❌ Unexpected error during token exchange: {str(e)}")
            return {
                "success": False,
                "error": "unexpected_error",
                "redirect_url": "fitpro://callback?error=unexpected_error&message=Unexpected error occurred"
            }

    @staticmethod
    async def make_api_request(db: AsyncSession, fitpro_user_id: str, endpoint: str, params: dict = None) -> Optional[Dict[str, Any]]:
        """
        Make authenticated request to Whoop API
        
        Args:
            fitpro_user_id: FitPro user ID (not Whoop user ID)
            endpoint: API endpoint (e.g., "user/profile/basic")
            params: Query parameters
        """
        # Get stored OAuth token
        token_data = await get_oauth_token(db, fitpro_user_id, 'whoop')
        if not token_data:
            raise ValueError("User not authenticated with Whoop")
        
        headers = {
            'Authorization': f"Bearer {token_data['access_token']}",
            'Content-Type': 'application/json'
        }
        
        url = f"{WHOOP_API_BASE_URL}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 401:
                raise ValueError("Access token expired. Please re-authenticate.")
            
            if response.status_code != 200:
                raise ValueError(f"Whoop API error: {response.text}")
            
            return response.json()
            
        except requests.RequestException as e:
            raise ValueError(f"Failed to connect to Whoop: {str(e)}")
    
    # Specific API methods
    @staticmethod
    async def get_user_profile(db: AsyncSession, fitpro_user_id: str) -> Optional[Dict[str, Any]]:
        """Get Whoop user profile"""
        return await WhoopIntegration.make_api_request(db, fitpro_user_id, "user/profile/basic")
    
    @staticmethod
    async def get_recovery_data(db: AsyncSession, fitpro_user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's recovery data"""
        return await WhoopIntegration.make_api_request(db, fitpro_user_id, "recovery")
    
    @staticmethod
    async def get_sleep_data(db: AsyncSession, fitpro_user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's sleep data"""
        return await WhoopIntegration.make_api_request(db, fitpro_user_id, "activity/sleep")
    
    @staticmethod
    async def get_workout_data(db: AsyncSession, fitpro_user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's workout data"""
        return await WhoopIntegration.make_api_request(db, fitpro_user_id, "activity/workout")
    
    @staticmethod
    async def get_specific_workout(db: AsyncSession, fitpro_user_id: str, workout_id: str) -> Optional[Dict[str, Any]]:
        """Get specific workout by ID"""
        return await WhoopIntegration.make_api_request(db, fitpro_user_id, f"activity/workout/{workout_id}")
    
    @staticmethod
    async def unlink_account(db: AsyncSession, fitpro_user_id: str) -> bool:
        """Remove Whoop connection for FitPro user"""
        try:
            
            # Remove OAuth tokens
            await db.execute(
                delete(OAuthToken).where(
                    OAuthToken.user_id == fitpro_user_id,
                    OAuthToken.provider_name == 'whoop'
                )
            )
            
            # Clear Whoop user ID from user record
            fitpro_user = await db.get(User, fitpro_user_id)
            if fitpro_user:
                fitpro_user.whoop_user_id = None
            
            await db.commit()
            return True
            
        except Exception as e:
            print(f"Error unlinking Whoop: {e}")
            await db.rollback()
            return False

        
