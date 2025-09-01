import os
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, Date
from sqlalchemy.sql import func
import redis.asyncio as redis
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Using DATABASE_URL: {DATABASE_URL}") 
engine = create_async_engine(DATABASE_URL, pool_size=20, max_overflow=0,pool_pre_ping=True,echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession)

REDIS_URL = os.getenv("REDIS_URL")
try:
    redis_client = redis.from_url(REDIS_URL)
except Exception as e:
    print(f"Redis connection failed: {e}")
    redis_client = None
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable must be set")
if not REDIS_URL:
    raise ValueError("REDIS_URL environment variable must be set")

class Base(DeclarativeBase):
    pass

# fitpro app users
class User(Base):
    __tablename__ = "users"

    #fitpro's internal user id
    user_id = Column(String(36), primary_key=True)

    # core authentication fields
    email = Column(String(256), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)

    # fitpro's users info
    username = Column(String(50), unique=True, nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    display_name = Column(String(150), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    
    # Privacy settings
    profile_visibility = Column(String(20), default="private")  # private, friends, public
    show_real_name = Column(Boolean, default=False)
    show_last_name = Column(Boolean, default=False)

    # ids for linked accounts
    whoop_user_id = Column(String(255), unique=True, nullable=True)
    spotify_user_id = Column(String(255), unique=True, nullable=True)

    # App metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    subscription_tier = Column(String(20), default="free")
    


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    token_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    provider_name = Column(String(50), nullable=False)

    # encrypted token data
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # token metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class OAuthState(Base):
    __tablename__ = "oauth_states"
    
    state = Column(String(255), primary_key=True)  # The OAuth state parameter
    provider_name = Column(String(50), nullable=False)  # "whoop", "spotify", etc.
    fitpro_user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    code_verifier = Column(Text, nullable=True)  # For PKCE (Whoop needs this)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    extra_data = Column(Text, nullable=True) 
    
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()    
async def get_redis():
    if redis_client is None:
        raise RuntimeError("Redis client is not available")
    return redis_client