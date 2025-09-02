import asyncio
import os
from dotenv import load_dotenv
from databases.database import AsyncSessionLocal

async def test_db():
    load_dotenv()
    print(f"Testing database connection...")
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute("SELECT 1")
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_db())