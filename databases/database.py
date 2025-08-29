import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, DateTime, Text, UUID, Boolean, ForeignKey
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

class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String(256), unique=True, nullable=False)
    username = Column(String(50), unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    token_id = Column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID, ForeignKey("users.user_id"), nullable=False)
    provider_name = Column(String(50), nullable=False)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


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