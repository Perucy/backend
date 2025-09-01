import os
import jwt
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv
from databases.database import User
from .dependencies import *

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable must be set")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30
# ================================================================================================
# JWT TOKEN FUNCTIONS
# ================================================================================================
def create_token_pair(user_data: dict) -> Dict[str, str]:
    access_payload = {
        "sub": user_data["user_id"],
        "email": user_data["email"],
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=ALGORITHM)

    refresh_payload = {
        "sub": user_data["user_id"],
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    }
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != token_type:
            return None
        
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    
# ================================================================================================
# PASSWORD HASHING
# ================================================================================================
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}:{pwd_hash.hex()}"

def verify_password(password: str, hashed_password: str) -> bool:
    try:
        salt, stored_hash = hashed_password.split(':')
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return stored_hash == pwd_hash.hex()
    except ValueError:
        return False
    
# ================================================================================================
# AUTHENTICATION FUNCTIONS
# ================================================================================================
async def register_user(db: AsyncSession, email: str, password: str, first_name: str, last_name: str, user_name: str):
    # check if user already exists
    existing_user = await get_user_by_email(db, email)
    if existing_user:
        raise ValueError("User with this email already exists")
    
    user_id = str(uuid.uuid4())
    hashed_pwd = hash_password(password)

    user_data = {
        'user_id':user_id,
        'email':email,
        'username':user_name,
        'first_name':first_name,
        'last_name':last_name,
        'password_hash':hashed_pwd
    }

    user = await create_user(db, user_data)

    tokens = create_token_pair({
        "user_id": user.user_id,
        "email": user.email
    })

async def login_user(db: AsyncSession, email: str, password: str) -> dict:
    user = await get_user_by_email(db, email)
    if not user:
        raise ValueError("Invalid email or password")
    
    if not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password")
    
    if not user.is_active:
        raise ValueError("Account is deactivated")
    
    tokens = create_token_pair({
        "user_id": user.user_id,
        "email": user.email
    })

    return {
        "user_id": user.user_id,
        "email": user.email,
        "username": user.username,
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_in": tokens["expires_in"],
        "token_type": "bearer"
    }

async def get_current_user(db: AsyncSession, token: str) -> User:
    payload = verify_token(token, "access")
    if not payload:
        raise ValueError("Invalid or expired access token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("Invalid token")
    
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError("User not found")
    
    return user

async def refresh_access_token(db: AsyncSession, refresh_token: str) -> dict:
    payload = verify_token(refresh_token, "refresh")
    if not payload:
        raise ValueError("Invalid or expired refresh token")
    
    user_id = payload.get("sub")

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise ValueError("User not found or inactive")
    
    new_access_payload = {
        "sub": user_id,
        "email": user.email,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    new_access_token = jwt.encode(new_access_payload, JWT_SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": new_access_token,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "token_type": "bearer"
    }