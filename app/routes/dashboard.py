"""
Dashboard routes - User dashboard and settings.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import logging

from app.middleware.auth import require_auth
from app.services.supabase_client import supabase_client
from datetime import datetime

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user_id: str = Depends(require_auth())):
    """
    User dashboard page.

    Shows:
    - Usage stats
    - Recent tests
    - API key status
    - Subscription info
    """
    try:
        # Get user profile
        profile_response = supabase_client.table("profiles").select("*").eq("id", user_id).single().execute()
        profile = profile_response.data

        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Check if user has API key
        api_key_response = supabase_client.table("user_api_keys").select("id, key_verified").eq("user_id", user_id).execute()
        has_api_key = len(api_key_response.data) > 0 and api_key_response.data[0].get("key_verified", False)

        # Get recent tests (limit to 10)
        tests_response = supabase_client.table("thumbnail_tests") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(10) \
            .execute()

        recent_tests = tests_response.data or []

        # Parse and format datetime strings
        for test in recent_tests:
            if test.get("created_at"):
                created_at_dt = datetime.fromisoformat(test["created_at"].replace("Z", "+00:00"))
                test["created_at_formatted"] = created_at_dt.strftime('%b %d, %Y at %I:%M %p')

        # Get user info from session
        from app.utils.session import get_session_data, get_access_token
        session_data = get_session_data(request)
        access_token = get_access_token(request)

        # Get user info using their access token (not admin API)
        user_email = None
        if access_token:
            try:
                user_response = supabase_client.auth.get_user(access_token)
                user_email = user_response.user.email if user_response.user else None
            except Exception as e:
                logger.warning(f"Failed to get user email: {e}")

        user = {
            "email": user_email,
            "full_name": profile.get("full_name"),
            "avatar_url": profile.get("avatar_url")
        }

        # Get creator profile
        from app.services.creator_profile_service import CreatorProfileService
        profile_service = CreatorProfileService()
        creator_profile = profile_service.get_user_profile(user_id)
        
        logger.info(f"Dashboard: User {user_id} - Profile found: {creator_profile is not None}")

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": user,
                "profile": profile,
                "creator_profile": creator_profile,
                "has_api_key": has_api_key,
                "recent_tests": recent_tests
            }
        )

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard")


@router.get("/test/{test_id}", response_class=HTMLResponse)
async def view_test(request: Request, test_id: str, user_id: str = Depends(require_auth())):
    """
    View a specific test result - redirects to preview page.
    """
    # Redirect to the preview page which has the full interactive grid
    return RedirectResponse(url=f"/preview/{test_id}", status_code=303)
