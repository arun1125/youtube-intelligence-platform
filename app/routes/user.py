"""
User API routes - Profile, API keys, settings.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
import logging

from app.middleware.auth import require_auth
from app.services.supabase_client import supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["user"])


class APIKeyCreate(BaseModel):
    """Request to add Google API key."""
    api_key: str


@router.post("/api-key")
async def add_api_key(
    request: Request,
    data: APIKeyCreate,
    user_id: str = Depends(require_auth())
):
    """
    Add or update user's Google API key.
    """
    try:
        # TODO: Validate API key by making test call to YouTube API
        # TODO: Encrypt API key before storing

        # For now, just store it (in production, encrypt this!)
        api_key_data = {
            "user_id": user_id,
            "google_api_key_encrypted": data.api_key,  # TODO: Encrypt
            "key_verified": True,  # TODO: Actually verify
            "last_verified_at": "now()"
        }

        # Check if key exists
        existing = supabase_client.table("user_api_keys") \
            .select("id") \
            .eq("user_id", user_id) \
            .execute()

        if existing.data:
            # Update existing
            supabase_client.table("user_api_keys") \
                .update(api_key_data) \
                .eq("user_id", user_id) \
                .execute()
        else:
            # Insert new
            supabase_client.table("user_api_keys") \
                .insert(api_key_data) \
                .execute()

        logger.info(f"✓ API key added/updated for user {user_id}")

        return {"success": True, "message": "API key saved successfully"}

    except Exception as e:
        logger.error(f"Failed to save API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to save API key")


@router.delete("/api-key")
async def remove_api_key(
    request: Request,
    user_id: str = Depends(require_auth())
):
    """
    Remove user's Google API key.
    """
    try:
        supabase_client.table("user_api_keys") \
            .delete() \
            .eq("user_id", user_id) \
            .execute()

        logger.info(f"✓ API key removed for user {user_id}")

        return {"success": True, "message": "API key removed"}

    except Exception as e:
        logger.error(f"Failed to remove API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove API key")


@router.get("/profile")
async def get_profile(
    request: Request,
    user_id: str = Depends(require_auth())
):
    """
    Get user profile.
    """
    try:
        profile_response = supabase_client.table("profiles") \
            .select("*") \
            .eq("id", user_id) \
            .single() \
            .execute()

        if not profile_response.data:
            raise HTTPException(status_code=404, detail="Profile not found")

        return profile_response.data

    except Exception as e:
        logger.error(f"Failed to get profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to load profile")
