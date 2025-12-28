"""
Authentication routes - Google OAuth flow.
"""

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
import logging

from .auth_service import auth_service
from app.utils.session import (
    create_session_cookie,
    clear_session_cookie,
    is_authenticated,
    get_access_token,
    get_user_id
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(redirect_to: str = "/dashboard"):
    """
    Initiate Google OAuth login flow.

    Args:
        redirect_to: URL to redirect after successful login (default: /dashboard)

    Returns:
        Redirect to Google OAuth consent screen
    """
    try:
        # Get Google OAuth URL
        oauth_url = auth_service.get_google_oauth_url(redirect_to=redirect_to)

        # Redirect to Google
        return RedirectResponse(url=oauth_url, status_code=302)

    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate login")


@router.get("/callback")
async def auth_callback(
    request: Request,
    response: Response,
    code: str = None,
    error: str = None,
    error_description: str = None,
    next: str = "/dashboard"
):
    """
    Handle OAuth callback from Google.

    Args:
        request: FastAPI request
        response: FastAPI response
        code: OAuth authorization code
        error: Error code from OAuth provider
        error_description: Error description
        next: URL to redirect after successful authentication

    Returns:
        Redirect to dashboard or specified URL
    """
    # Handle OAuth errors from Supabase
    if error:
        error_msg = error_description or error
        logger.error(f"OAuth callback error: {error} - {error_description}")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=302)

    if not code:
        logger.error("No code provided in OAuth callback")
        return RedirectResponse(url="/?error=no_code", status_code=302)

    try:
        # Exchange code for session
        session_data = auth_service.exchange_code_for_session(code)

        # Ensure profile exists
        profile = auth_service.get_or_create_profile(session_data["user_id"])

        if not profile:
            logger.error(f"Failed to create profile for user {session_data['user_id']}")
            raise HTTPException(status_code=500, detail="Failed to create user profile")

        logger.info(f"✓ User {session_data['email']} logged in successfully")

        # Create redirect response
        redirect_response = RedirectResponse(url=next, status_code=302)

        # Set session cookie on redirect response
        create_session_cookie(
            response=redirect_response,
            user_id=session_data["user_id"],
            access_token=session_data["access_token"],
            refresh_token=session_data["refresh_token"],
            expires_at=session_data["expires_at"]
        )

        return redirect_response

    except Exception as e:
        logger.error(f"Auth callback failed: {e}")
        return RedirectResponse(url="/?error=auth_failed", status_code=302)


@router.get("/logout")
async def logout(request: Request, response: Response):
    """
    Log out user and clear session.

    Args:
        request: FastAPI request
        response: FastAPI response

    Returns:
        Redirect to home page
    """
    try:
        # Check if user is authenticated
        if is_authenticated(request):
            access_token = get_access_token(request)

            if access_token:
                # Sign out from Supabase
                auth_service.sign_out(access_token)

        logger.info("User logged out successfully")

        # Create redirect response
        redirect_response = RedirectResponse(url="/", status_code=302)

        # Clear session cookie on redirect response
        clear_session_cookie(redirect_response)

        return redirect_response

    except Exception as e:
        logger.error(f"Logout failed: {e}")
        # Still clear cookie even if sign out fails
        redirect_response = RedirectResponse(url="/", status_code=302)
        clear_session_cookie(redirect_response)
        return redirect_response


@router.get("/me")
async def get_current_user(request: Request):
    """
    Get current authenticated user info.

    Args:
        request: FastAPI request

    Returns:
        User info dict
    """
    access_token = get_access_token(request)

    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_info = auth_service.get_user_from_token(access_token)

    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid session")

    return user_info


@router.get("/status")
async def auth_status(request: Request):
    """
    Check authentication status.

    Args:
        request: FastAPI request

    Returns:
        Dict with authentication status
    """
    authenticated = is_authenticated(request)

    return {
        "authenticated": authenticated,
        "user_id": None if not authenticated else get_user_id(request)
    }
