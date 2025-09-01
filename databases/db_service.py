from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .database import User, OAuthToken
from cryptography.fernet import Fernet
import os
import uuid
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
    print(f"Storing OAuth token - User: {user_id}, Provider: {provider}")

    encrypted_access = fernet.encrypt(access_token.encode()).decode()
    encrypted_refresh = fernet.encrypt(refresh_token.encode()).decode() if refresh_token else None

    expires_at = datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None

    try:
        result = await db.execute(
            select(OAuthToken).where(
                OAuthToken.user_id == user_id,
                OAuthToken.provider_name == provider
            )
        )
        print("db results:", result)
        existing_token = result.scalar_one_or_none()
        if existing_token:
            print(f"Updating existing {provider} token for user {user_id}")
            # Update existing token
            existing_token.access_token_encrypted = encrypted_access
            existing_token.refresh_token_encrypted = encrypted_refresh
            existing_token.expires_at = expires_at
        else:
            print(f"Creating new {provider} token for user {user_id}")
            # Create new token with app-generated ID
            token_id = str(uuid.uuid4())
            new_token = OAuthToken(
                token_id=token_id,
                user_id=user_id,
                provider_name=provider,
                access_token_encrypted=encrypted_access,
                refresh_token_encrypted=encrypted_refresh,
                expires_at=expires_at
            )
            db.add(new_token)

        await db.commit()
        print(f"Successfully stored {provider} OAuth token for user {user_id}")

    except Exception as db_error:
        print(f"Database query error: {db_error}")
        await db.rollback()
        raise

async def get_oauth_token(db: AsyncSession, user_id: str, provider: str):
    try:
        result = await db.execute(
            select(OAuthToken).where(
                OAuthToken.user_id == user_id,
                OAuthToken.provider_name == provider
            )
        )

        print("db results:", result)
        token = result.scalar_one_or_none()

        if not token:
            print(f"No {provider} token found for user {user_id}")
            return None
        
        access_token = fernet.decrypt(token.access_token_encrypted.encode()).decode()
        refresh_token = fernet.decrypt(token.refresh_token_encrypted.encode()).decode() if token.refresh_token_encrypted else None

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': token.expires_at
        }
    except Exception as db_error:
        print(f"Database error retrieving OAuth token: {db_error}")
        return None