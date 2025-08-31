from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from databases.database import User
from typing import Optional, Dict

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user_data: dict) -> User:
    new_user = User(
        user_id=user_data['user_id'],
        email=user_data['email'],
        username=user_data['username'],
        first_name=user_data['first_name'],
        last_name=user_data['last_name'],
        password_hash=user_data['password_hash']
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user