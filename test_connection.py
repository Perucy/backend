import asyncio
import os
from dotenv import load_dotenv
from databases.database import AsyncSessionLocal
from sqlalchemy import text

async def test_connection_and_tables():
    """Test both connection and tables in one async session"""
    load_dotenv()
    print(f"Testing database connection and tables...")
    
    try:
        async with AsyncSessionLocal() as session:
            # Test basic connection
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            print(f"✅ Database connection successful! Result: {value}")
            
            # Check if tables exist
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = result.fetchall()
            
            if tables:
                print("✅ Found tables:")
                for table in tables:
                    print(f"  - {table[0]}")
                print(f"\n✅ Database is ready! Found {len(tables)} tables.")
                return True
            else:
                print("⚠️ No tables found - you need to run the SQL schema")
                return False
                
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection_and_tables())
    if success:
        print("\n🎉 Your database is ready for the FitPro app!")
    else:
        print("\n❌ Database setup incomplete.")