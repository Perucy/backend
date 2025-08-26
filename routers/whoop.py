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

whoop_router = APIRouter()

# Whoop config
WHOOP_CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
WHOOP_CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
WHOOP_REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI")

# whoop api urls
WHOOP_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_API_BASE_URL = "https://api.prod.whoop.com/developer/v2"

whoop_user_tokens = {}
whoop_auth_states = {}

def generate_code_verifier():
    """Generate PKCE code verifier"""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

def generate_code_challenge(verifier: str):
    """Generate PKCE code challenge"""
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')

@whoop_router.get("/auth/login")  # Fixed: Removed duplicate "/whoop"
async def initiate_whoop_login():
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
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

@whoop_router.get("/auth/callback")  # Fixed: Removed duplicate "/whoop"
async def whoop_auth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None, 
    error: Optional[str] = None
):
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
    if state not in whoop_auth_states:
        print(f"❌ Invalid or expired state parameter: {state}")
        error_url = "fitpro://callback?error=invalid_state&message=Invalid or expired request"
        return RedirectResponse(url=error_url)
    
    code_verifier = whoop_auth_states[state]['code_verifier']
    del whoop_auth_states[state]  # Clean up
    
    # Exchange authorization code for access token
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': WHOOP_REDIRECT_URI,
        'client_id': WHOOP_CLIENT_ID,
        'client_secret': WHOOP_CLIENT_SECRET,
        'code_verifier': code_verifier
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        # Get access token
        print(f"🔄 Exchanging code for access token...")
        token_response = requests.post(WHOOP_TOKEN_URL, data=token_data, headers=headers)
        
        if token_response.status_code != 200:
            print(f"❌ Token exchange failed: {token_response.status_code} - {token_response.text}")
            error_url = "fitpro://callback?error=token_exchange_failed&message=Failed to exchange authorization code"
            return RedirectResponse(url=error_url)
        
        token_info = token_response.json()
        access_token = token_info['access_token']
        
        # Get user profile
        print(f"🔄 Fetching user profile...")
        profile_response = requests.get(
            f"{WHOOP_API_BASE_URL}/user/profile/basic",  # Fixed: Use correct Whoop endpoint
            headers={'Authorization': f"Bearer {access_token}"}
        )
        
        if profile_response.status_code != 200:
            print(f"❌ Profile fetch failed: {profile_response.status_code} - {profile_response.text}")
            error_url = "fitpro://callback?error=profile_fetch_failed&message=Failed to retrieve user profile"
            return RedirectResponse(url=error_url)
        
        user_profile = profile_response.json()
        # Fixed: Whoop API returns 'user_id' not 'id'
        user_id = user_profile.get('user_id') or str(user_profile.get('id', secrets.token_hex(8)))
        
        # Store user tokens and profile
        whoop_user_tokens[user_id] = {
            'access_token': access_token,
            'refresh_token': token_info.get('refresh_token'),
            'expires_in': token_info.get('expires_in'),
            'profile': user_profile
        }
        
        # Fixed: Use appropriate field for display name
        display_name = user_profile.get('first_name', user_profile.get('email', 'Whoop User'))
        print(f"✅ OAuth successful for user: {display_name} ({user_id})")
        
        # Redirect to mobile app with success
        from urllib.parse import quote
        display_name_encoded = quote(display_name)
        success_url = f"fitpro://callback?success=true&user_id={user_id}&display_name={display_name_encoded}"
        return RedirectResponse(url=success_url)
    
    except requests.RequestException as e:
        print(f"❌ Network error during token exchange: {str(e)}")
        error_url = "fitpro://callback?error=network_error&message=Network error during authentication"
        return RedirectResponse(url=error_url)
    except Exception as e:
        print(f"❌ Unexpected error during token exchange: {str(e)}")
        error_url = "fitpro://callback?error=unexpected_error&message=Unexpected error occurred"
        return RedirectResponse(url=error_url)
    
def get_whoop_user_access_token(user_id: int) -> str:
    """Get access token for user"""
    print(f"Looking for user_id: {user_id} (type: {type(user_id)})")
    print(f"Available keys: {list(whoop_user_tokens.keys())} (types: {[type(k) for k in whoop_user_tokens.keys()]})")
    
    # Convert user_id to string to ensure consistent lookup
    # user_id_str = str(user_id)

    print("whoop user tokens:", whoop_user_tokens)  # Debugging line
    
    if user_id not in whoop_user_tokens:
        raise HTTPException(status_code=401, detail="User not authenticated")
    return whoop_user_tokens[user_id]['access_token']

async def make_whoop_request(user_id: str, endpoint: str, params: dict = None):
    """Make authenticated request to Whoop API"""  # Fixed: Updated comment
    access_token = get_whoop_user_access_token(user_id)

    print("Access token:", access_token)  # Debugging line
    print("User ID:", user_id)  # Debugging line
    print("Endpoint:", endpoint)  # Debugging line
    print("Params:", params)  # Debugging line
    
    headers = {
        'Authorization': f"Bearer {access_token}",
        'Content-Type': 'application/json'
    }
    
    url = f"{WHOOP_API_BASE_URL}/{endpoint.lstrip('/')}"

    print("url:", url)  # Debugging line
    
    try:
        response = requests.get(url, headers=headers, params=params)

        print("response:", response)
        
        if response.status_code == 401:
            # Token might be expired
            raise HTTPException(status_code=401, detail="Access token expired. Please re-authenticate.")
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Whoop API error: {response.text}"
            )
        
        return response.json()
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Whoop: {str(e)}")

@whoop_router.get("/api/user/{user_id}/profile")
async def whoop_user_profile(user_id: int):
    """Get user's Whoop profile"""
    print(f"🔍 Profile request for user: {user_id}, {type(user_id)}")
    print(f"🔍 Available users: {list(whoop_user_tokens.keys())}")
    
    if user_id in whoop_user_tokens:
        print(f"🔍 User found, making API request to Whoop...")
    else:
        print(f"🔍 User not found in tokens")
    
    try:
        result = await make_whoop_request(user_id, "user/profile/basic")
        print(f"🔍 Whoop API response: {result}")
        return result
    except Exception as e:
        print(f"🔍 Whoop API error: {e}")
        raise

@whoop_router.get("/api/user/{user_id}/workout/{workout_id}")  # Fixed: Added missing workout_id in path
async def whoop_user_workout(user_id: str, workout_id: str):
    """Get user's workout by ID"""
    return await make_whoop_request(user_id, f"activity/workout/{workout_id}")

@whoop_router.get("/api/user/{user_id}/collection/workout")
async def whoop_user_workout_collections(user_id: str):
    """Get details of workouts collection"""
    return await make_whoop_request(user_id, "activity/workout")

@whoop_router.get("/api/user/{user_id}/sleep/{sleep_id}")  # Fixed: Changed sleepId to sleep_id (snake_case)
async def whoop_user_sleep(user_id: str, sleep_id: str):
    """Get user's sleep by ID"""
    return await make_whoop_request(user_id, f"activity/sleep/{sleep_id}")

@whoop_router.get("/api/user/{user_id}/collection/sleep")
async def whoop_user_sleep_collections(user_id: str):
    """Get details of sleep collection"""
    return await make_whoop_request(user_id, "activity/sleep")

@whoop_router.get("/api/user/{user_id}/collection/recovery")
async def whoop_user_recovery_collections(user_id: str):
    """Get details of recovery collection"""
    return await make_whoop_request(user_id, "recovery")

@whoop_router.get("/api/user/{user_id}/cycle/{cycle_id}/recovery")  # Fixed: URL path and parameter name
async def whoop_user_recovery_for_cycle(user_id: str, cycle_id: str):  # Fixed: Function name typo
    """Get details of recovery for cycle"""
    return await make_whoop_request(user_id, f"cycle/{cycle_id}/recovery")

@whoop_router.get("/api/user/{user_id}/cycle/{cycle_id}")  # Fixed: Changed cycleId to cycle_id
async def whoop_user_cycle(user_id: str, cycle_id: str):
    """Get details of cycle by ID"""
    return await make_whoop_request(user_id, f"cycle/{cycle_id}")

@whoop_router.get("/api/user/{user_id}/collection/cycle")
async def whoop_user_cycle_collections(user_id: str):  # Fixed: Function name (was duplicate)
    """Get details of cycle collection"""
    return await make_whoop_request(user_id, "cycle")

@whoop_router.delete("/api/user/{user_id}/disconnect")
async def whoop_disconnect_user(user_id: str):
    """Disconnect user from Whoop"""
    if user_id in whoop_user_tokens:
        del whoop_user_tokens[user_id]
        return {"message": "Successfully disconnected from Whoop"}
    else:
        raise HTTPException(status_code=404, detail="User not found")

@whoop_router.get("/api/user/{user_id}/status")
async def whoop_get_user_status(user_id: str):  # Fixed: Function name conflict
    """Check if user is still authenticated"""
    if user_id in whoop_user_tokens:
        profile = whoop_user_tokens[user_id]['profile']
        return {
            "authenticated": True,
            "user_id": user_id,
            "display_name": profile.get('first_name', profile.get('email', 'Whoop User')),  # Fixed: Use correct field
            "email": profile.get('email')
        }
    else:
        raise HTTPException(status_code=404, detail="User not authenticated")