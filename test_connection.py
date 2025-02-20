import asyncio
from src.core.dependencies import create_supabase_client

async def test_connection():
    client = None
    try:
        client = await create_supabase_client()
        print("Supabase connection successful!")
    except Exception as e:
        print(f"Connection failed: {str(e)}")
    finally:
        if client:
            await client.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
