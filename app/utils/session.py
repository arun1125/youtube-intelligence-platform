"""
Session management utilities.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import Request, Response
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Session serializer (for signing cookies)
serializer = URLSafeTimedSerializer(settings.supabase_secret_key)

# Session cookie name
SESSION_COOKIE_NAME = "session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def create_session_cookie(
    response: Response,
    user_id: str,
    access_token: str,
    refresh_token: str,
    expires_at: int
) -> None:
    """
    Create encrypted session cookie.

    Args:
        response: FastAPI response object
        user_id: User's UUID
        access_token: JWT access token
        refresh_token: JWT refresh token
        expires_at: Token expiration timestamp
    """
    session_data = {
        "user_id": user_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at
    }

    # Serialize and sign
    signed_data = serializer.dumps(session_data)

    # Set secure cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=signed_data,
        max_age=SESSION_MAX_AGE,
        httponly=True,  # Prevent JS access
        secure=not settings.debug,  # HTTPS only in production
        samesite="lax"
    )

    logger.debug(f"Session cookie created for user {user_id}")


def get_session_data(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get session data from cookie.

    Args:
        request: FastAPI request object

    Returns:
        Session data dict or None if invalid/expired
    """
    cookie_value = request.cookies.get(SESSION_COOKIE_NAME)

    if not cookie_value:
        return None

    try:
        # Deserialize and verify signature
        session_data = serializer.loads(
            cookie_value,
            max_age=SESSION_MAX_AGE
        )

        # Check if token is expired
        if session_data.get("expires_at"):
            if datetime.now().timestamp() > session_data["expires_at"]:
                logger.debug("Session token expired")
                return None

        return session_data

    except SignatureExpired:
        logger.debug("Session cookie expired")
        return None
    except BadSignature:
        logger.warning("Invalid session cookie signature")
        return None
    except Exception as e:
        logger.error(f"Failed to load session: {e}")
        return None


def clear_session_cookie(response: Response) -> None:
    """
    Clear session cookie.

    Args:
        response: FastAPI response object
    """
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=not settings.debug,
        samesite="lax"
    )

    logger.debug("Session cookie cleared")


def get_user_id(request: Request) -> Optional[str]:
    """
    Get user ID from session.

    Args:
        request: FastAPI request object

    Returns:
        User ID or None
    """
    session_data = get_session_data(request)
    return session_data.get("user_id") if session_data else None


def get_access_token(request: Request) -> Optional[str]:
    """
    Get access token from session.

    Args:
        request: FastAPI request object

    Returns:
        Access token or None
    """
    session_data = get_session_data(request)
    return session_data.get("access_token") if session_data else None


def is_authenticated(request: Request) -> bool:
    """
    Check if user is authenticated.

    Args:
        request: FastAPI request object

    Returns:
        True if authenticated
    """
    return get_session_data(request) is not None


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user.

    Args:
        request: FastAPI request object

    Returns:
        User info dict or None
    """
    access_token = get_access_token(request)
    
    if not access_token:
        return None

    from app.features.auth.auth_service import auth_service
    return auth_service.get_user_from_token(access_token)
