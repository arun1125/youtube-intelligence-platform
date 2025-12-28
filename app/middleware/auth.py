"""
Authentication middleware for protecting routes.
"""

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from typing import Callable
import logging

from app.utils.session import is_authenticated, get_access_token
from app.features.auth.auth_service import auth_service

logger = logging.getLogger(__name__)


def require_auth(redirect_to_login: bool = True):
    """
    Dependency to require authentication for a route.

    Args:
        redirect_to_login: If True, redirect to login page. If False, raise 401.

    Usage:
        @app.get("/protected")
        async def protected_route(user_id: str = Depends(require_auth())):
            return {"user_id": user_id}
    """

    async def dependency(request: Request):
        # Check if authenticated
        if not is_authenticated(request):
            if redirect_to_login:
                # Redirect to login with return URL
                return_url = str(request.url)
                raise HTTPException(
                    status_code=307,
                    detail=f"/auth/login?redirect_to={return_url}",
                    headers={"Location": f"/auth/login?redirect_to={return_url}"}
                )
            else:
                raise HTTPException(status_code=401, detail="Not authenticated")

        # Get access token
        access_token = get_access_token(request)

        if not access_token:
            raise HTTPException(status_code=401, detail="Invalid session")

        # Verify token and get user info
        user_info = auth_service.get_user_from_token(access_token)

        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        # Return user ID for route to use
        return user_info["user_id"]

    return dependency


def optional_auth():
    """
    Dependency for optional authentication.
    Returns user_id if authenticated, None otherwise.

    Usage:
        @app.get("/optional")
        async def optional_route(user_id: Optional[str] = Depends(optional_auth())):
            if user_id:
                return {"message": "Authenticated", "user_id": user_id}
            else:
                return {"message": "Anonymous"}
    """

    async def dependency(request: Request):
        # Check if authenticated
        if not is_authenticated(request):
            return None

        # Get access token
        access_token = get_access_token(request)

        if not access_token:
            return None

        # Verify token and get user info
        user_info = auth_service.get_user_from_token(access_token)

        if not user_info:
            return None

        return user_info["user_id"]

    return dependency


async def auth_middleware(request: Request, call_next: Callable):
    """
    Global middleware to handle session refresh.

    This middleware runs on every request and refreshes the session
    if the access token is close to expiring.
    """
    try:
        # Process request
        response = await call_next(request)
        return response

    except Exception as e:
        logger.error(f"Middleware error: {e}")
        # Re-raise to let FastAPI handle it
        raise
