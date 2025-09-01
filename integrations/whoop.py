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
from databases.

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

        # Fixed: Changed dictionary key from variable to string
        whoop_auth_states[state] = {
            'code_verifier': code_verifier,  # Fixed: Use string key, not variable
            "created_at": secrets.token_hex(16)
        }

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