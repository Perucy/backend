from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .database import User, OAuthToken
from cryptography.fernet import Fernet
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY environment variable must be set")

fernet = Fernet(ENCRYPTION_KEY.encode())

async def store_oauth_token(
    db: AsyncSession,
    user_id: str,
    provider: str,
    access_token: str,
    refresh_token: str = None,
    expires_in: int = None
):
    print("store oauth token")
    print("user id:", user_id)
    print("provider:", provider)

    encrypted_access = fernet.encrypt(access_token.encode()).decode()
    encrypted_refresh = fernet.encrypt(refresh_token.encode()).decode() if refresh_token else None

    expires_at = datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None

    print("encrypted access:", encrypted_access)
    print("encrypted_refresh:", encrypted_refresh)
    print("expires at", expires_at)
    print("db", db)

    try:
        result = await db.execute(
            select(OAuthToken).where(
                OAuthToken.user_id == user_id,
                OAuthToken.provider_name == provider
            )
        )
        print("db results:", result)
        existing_token = result.scalar_one_or_none()
        print("existing_token:", existing_token)
    except Exception as db_error:
        print(f"Database query error: {db_error}")
        raise
    
    print("db results:", result)
    existing_token = result.scalar_one_or_none()

    if existing_token:
        existing_token.access_token_encrypted = encrypted_access
        existing_token.refresh_token_encrypted = encrypted_refresh
        existing_token.expires_at = expires_at
    else:
        new_token = OAuthToken(
            user_id=user_id,
            provider_name=provider,
            access_token_encrypted=encrypted_access,
            refresh_token_encrypted=encrypted_refresh,
            expires_at=expires_at
        )
        db.add(new_token)

    await db.commit()

async def get_oauth_token(db: AsyncSession, user_id: str, provider: str):
    
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user_id,
            OAuthToken.provider_name == provider
        )
    )

    print("db results:", result)
    token = result.scalar_one_or_none()

    if not token:
        return None
    
    access_token = fernet.decrypt(token.access_token_encrypted.encode()).decode()
    refresh_token = fernet.decrypt(token.refresh_token_encrypted.encode()).decode() if token.refresh_token_encrypted else None

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_at': token.expires_at
    }