import asyncio
from app.services.creator_profile_service import CreatorProfileService

async def test_service():
    service = CreatorProfileService()
    user_id = "fc86a6ef-344f-4dd7-aac6-705f0bda7b65"
    exists = service.profile_exists(user_id)
    print(f"Profile exists for {user_id}: {exists}")

if __name__ == "__main__":
    asyncio.run(test_service())
