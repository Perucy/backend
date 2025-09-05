from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from databases.database import OAuthState
import json

class OAuthStateService:
    @staticmethod
    async def store_state(
        db: AsyncSession,
        state: str,
        provider_name: str,
        fitpro_user_id: str,
        code_verifier: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        expires_in_minutes: int = 10
    ) -> bool:
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
            
            oauth_state = OAuthState(
                state=state,
                provider_name=provider_name,
                fitpro_user_id=fitpro_user_id,
                code_verifier=code_verifier,
                expires_at=expires_at,
                extra_data=json.dumps(extra_data) if extra_data else None
            )
            
            db.add(oauth_state)
            await db.commit()
            return True
        except Exception as e:
            print(f"Error storing OAuth state: {e}")
            await db.rollback()
            return False
        
    @staticmethod
    async def get_and_delete_state(
        db: AsyncSession,
        state: str,
        provider_name: str
    ) -> Optional[Dict[str, Any]]:
        try:
            result = await db.execute(
                select(OAuthState).where(
                    OAuthState.state == state,
                    OAuthState.provider_name == provider_name
                )
            )
            oauth_state = result.scalar_one_or_none()
            print("🔗oauth state:", oauth_state)
            
            if not oauth_state:
                return None
            
            current_time = datetime.now(timezone.utc)
            # Check if expired
            if current_time > oauth_state.expires_at:
                # Delete expired state
                await db.execute(
                    delete(OAuthState).where(OAuthState.state == state)
                )
                await db.commit()
                return None
            
            # Extract data
            state_data = {
                "fitpro_user_id": oauth_state.fitpro_user_id,
                "code_verifier": oauth_state.code_verifier,
                "created_at": oauth_state.created_at,
                "extra_data": json.loads(oauth_state.extra_data) if oauth_state.extra_data else None
            }
            
            # Delete the state (one-time use)
            await db.execute(
                delete(OAuthState).where(OAuthState.state == state)
            )
            await db.commit()
            
            return state_data
        except Exception as e:
            print(f"Error retrieving OAuth state: {e}")
            await db.rollback()
            return None
        
    @staticmethod
    async def get_user_pending_states(db: AsyncSession, fitpro_user_id: str) -> list:
        """Get all pending OAuth states for a user (for debugging)"""
        try:
            result = await db.execute(
                select(OAuthState).where(
                    OAuthState.fitpro_user_id == fitpro_user_id,
                    OAuthState.expires_at > datetime.utcnow()
                )
            )
            states = result.scalars().all()
            
            return [
                {
                    "state": state.state,
                    "provider": state.provider_name,
                    "created_at": state.created_at,
                    "expires_at": state.expires_at
                }
                for state in states
            ]
            
        except Exception as e:
            print(f"Error getting user pending states: {e}")
            return []