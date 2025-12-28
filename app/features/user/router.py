"""
User API routes - Profile, API keys, settings.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
import logging
import httpx

from app.middleware.auth import require_auth
from app.core.database import supabase_client
from app.utils.encryption import encrypt_api_key, decrypt_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["user"])


class APIKeyCreate(BaseModel):
    """Request to add Google API key."""
    api_key: str


async def validate_youtube_api_key(api_key: str) -> bool:
    """
    Validate a YouTube API key by making a test call.

    Args:
        api_key: The YouTube Data API key to validate

    Returns:
        True if the key is valid, False otherwise
    """
    try:
        # Make a simple, low-quota API call to validate the key
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "key": api_key,
            "part": "id",
            "chart": "mostPopular",
            "maxResults": 1
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)

            if response.status_code == 200:
                return True
            elif response.status_code == 400:
                # Check if it's a key error or just bad request
                error_data = response.json()
                error_reason = error_data.get("error", {}).get("errors", [{}])[0].get("reason", "")
                if error_reason in ["keyInvalid", "keyExpired"]:
                    return False
                # Other 400 errors might still mean the key is valid
                return True
            elif response.status_code == 403:
                # Could be quota exceeded but key is still valid
                error_data = response.json()
                error_reason = error_data.get("error", {}).get("errors", [{}])[0].get("reason", "")
                if error_reason == "keyInvalid":
                    return False
                # Quota exceeded or API not enabled - key might still be valid format
                logger.warning(f"API key validation got 403: {error_reason}")
                return error_reason in ["quotaExceeded", "rateLimitExceeded", "accessNotConfigured"]
            else:
                logger.warning(f"API key validation got status {response.status_code}")
                return False

    except httpx.TimeoutException:
        logger.warning("API key validation timed out")
        # Timeout doesn't mean invalid key
        return True
    except Exception as e:
        logger.error(f"Error validating API key: {e}")
        return False


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
        # Step 1: Validate API key by making test call to YouTube API
        is_valid = await validate_youtube_api_key(data.api_key)

        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail="Invalid API key. Please check that your YouTube Data API key is correct and the API is enabled."
            )

        # Step 2: Encrypt API key before storing
        encrypted_key = encrypt_api_key(data.api_key)

        api_key_data = {
            "user_id": user_id,
            "google_api_key_encrypted": encrypted_key,
            "key_verified": True,
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

        logger.info(f"✓ API key added/updated for user {user_id} (encrypted and verified)")

        return {"success": True, "message": "API key saved successfully"}

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Encryption error: {e}")
        raise HTTPException(status_code=500, detail="Failed to encrypt API key")
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


@router.get("/api-key/status")
async def get_api_key_status(
    request: Request,
    user_id: str = Depends(require_auth())
):
    """
    Check if user has a configured API key.

    Returns:
        has_key: Whether the user has an API key configured
        key_verified: Whether the key has been verified
        last_verified_at: When the key was last verified
    """
    try:
        key_response = supabase_client.table("user_api_keys") \
            .select("key_verified, last_verified_at") \
            .eq("user_id", user_id) \
            .execute()

        if key_response.data and len(key_response.data) > 0:
            key_data = key_response.data[0]
            return {
                "has_key": True,
                "key_verified": key_data.get("key_verified", False),
                "last_verified_at": key_data.get("last_verified_at")
            }
        else:
            return {
                "has_key": False,
                "key_verified": False,
                "last_verified_at": None
            }

    except Exception as e:
        logger.error(f"Failed to get API key status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get API key status")


def get_user_api_key(user_id: str) -> str | None:
    """
    Retrieve and decrypt a user's API key.

    Args:
        user_id: The user's ID

    Returns:
        The decrypted API key, or None if not found
    """
    try:
        key_response = supabase_client.table("user_api_keys") \
            .select("google_api_key_encrypted, key_verified") \
            .eq("user_id", user_id) \
            .execute()

        if not key_response.data or len(key_response.data) == 0:
            return None

        key_data = key_response.data[0]
        encrypted_key = key_data.get("google_api_key_encrypted")

        if not encrypted_key:
            return None

        # Decrypt the key
        return decrypt_api_key(encrypted_key)

    except Exception as e:
        logger.error(f"Failed to retrieve API key for user {user_id}: {e}")
        return None


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
