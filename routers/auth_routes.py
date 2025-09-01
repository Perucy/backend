from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from databases.database import get_db
from auth.auth import register_user, refresh_access_token, login_user
from pydantic import BaseModel

router = APIRouter()

class UserRegistration(BaseModel):
    email: str
    password: str
    username: str
    first_name: str
    last_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/register")
async def register(user_data: UserRegistration, db: AsyncSession = Depends(get_db)):
    try:
        result = await register_user(db, user_data.email, user_data.password, user_data.first_name, user_data.last_name, user_data.username)
        return result
    except ValueError as e:
        raise HTTPException
    
@router.post("/login")
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        result = await login_user(db, login_data.email, login_data.password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/refresh")
async def login(token_request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await refresh_access_token(db, token_request.refresh_token)
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))