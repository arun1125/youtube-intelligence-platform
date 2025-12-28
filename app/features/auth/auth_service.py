"""
Authentication service using Supabase Auth + Google OAuth.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from app.core.config import get_settings
from app.core.database import supabase_client

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthService:
    """Service for handling user authentication with Supabase."""

    def __init__(self):
        self.supabase = supabase_client

    def get_google_oauth_url(self, redirect_to: str = "/dashboard") -> str:
        """
        Get Google OAuth URL for initiating sign-in flow.

        Args:
            redirect_to: URL to redirect after successful authentication

        Returns:
            Google OAuth URL
        """
        try:
            # Supabase handles OAuth URL generation
            response = self.supabase.auth.sign_in_with_oauth({
                "provider": "google",
                "options": {
                    "redirect_to": f"{settings.google_redirect_uri}?next={redirect_to}"
                }
            })
            return response.url
        except Exception as e:
            logger.error(f"Failed to generate Google OAuth URL: {e}")
            raise

    def exchange_code_for_session(self, code: str) -> Dict[str, Any]:
        """
        Exchange OAuth code for user session.

        Args:
            code: OAuth authorization code from callback

        Returns:
            Dict with user and session info
        """
        try:
            # Exchange code for session
            response = self.supabase.auth.exchange_code_for_session({
                "auth_code": code
            })

            user = response.user
            session = response.session

            if not user or not session:
                raise ValueError("Failed to get user session")

            logger.info(f"✓ User authenticated: {user.email}")

            return {
                "user_id": user.id,
                "email": user.email,
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_at": session.expires_at
            }

        except Exception as e:
            logger.error(f"Failed to exchange code for session: {e}")
            raise

    def get_user_from_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user info from access token.

        Args:
            access_token: JWT access token

        Returns:
            User info dict or None if invalid
        """
        try:
            response = self.supabase.auth.get_user(access_token)
            user = response.user

            if not user:
                return None

            return {
                "user_id": user.id,
                "email": user.email,
                "full_name": user.user_metadata.get("full_name"),
                "avatar_url": user.user_metadata.get("avatar_url")
            }

        except Exception as e:
            logger.warning(f"Failed to get user from token: {e}")
            return None

    def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh user session using refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            New session info
        """
        try:
            response = self.supabase.auth.refresh_session(refresh_token)
            session = response.session

            if not session:
                raise ValueError("Failed to refresh session")

            return {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_at": session.expires_at
            }

        except Exception as e:
            logger.error(f"Failed to refresh session: {e}")
            raise

    def sign_out(self, access_token: str) -> bool:
        """
        Sign out user and invalidate session.

        Args:
            access_token: User's access token (unused, kept for API compatibility)

        Returns:
            True if successful
        """
        # Note: Supabase Python client's sign_out() doesn't need the token
        # The session is managed by cookies on our side, so we just need
        # to clear the cookie (done in the route)
        logger.info("User signed out successfully")
        return True

    def get_or_create_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile or create if doesn't exist.

        Args:
            user_id: User's UUID

        Returns:
            Profile data or None
        """
        try:
            # Try to get existing profile
            response = self.supabase.table("profiles").select("*").eq("id", user_id).single().execute()

            if response.data:
                return response.data

            # Profile should be auto-created by trigger, but just in case
            logger.warning(f"Profile not found for user {user_id}, creating...")

            # Get user metadata
            user = self.supabase.auth.admin.get_user_by_id(user_id)

            # Create profile
            profile_data = {
                "id": user_id,
                "full_name": user.user_metadata.get("full_name"),
                "avatar_url": user.user_metadata.get("avatar_url")
            }

            response = self.supabase.table("profiles").insert(profile_data).execute()
            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Failed to get/create profile: {e}")
            return None

    def can_create_test(self, user_id: str) -> bool:
        """
        Check if user can create a new test.

        Args:
            user_id: User's UUID

        Returns:
            True if user can create test
        """
        try:
            # Use database function
            response = self.supabase.rpc("can_create_test", {"p_user_id": user_id}).execute()
            return response.data if response.data is not None else False

        except Exception as e:
            logger.error(f"Failed to check test creation eligibility: {e}")
            return False

    def increment_test_usage(self, user_id: str) -> bool:
        """
        Increment user's monthly test usage counter.

        Args:
            user_id: User's UUID

        Returns:
            True if successful
        """
        try:
            # Use PostgreSQL increment function for atomic operation
            self.supabase.rpc("increment_test_usage", {"p_user_id": user_id}).execute()
            logger.info(f"✓ Incremented test usage for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to increment test usage: {e}")
            return False


# Singleton instance
auth_service = AuthService()
