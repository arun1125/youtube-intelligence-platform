import asyncio
from app.services.supabase_client import get_supabase_client

async def check_profiles():
    supabase = get_supabase_client()
    try:
        response = supabase.table('user_creator_profile').select('*').execute()
        print(f"Total profiles: {len(response.data)}")
        for p in response.data:
            print(f"User ID: {p.get('user_id')}, Name: {p.get('creator_name')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_profiles())
