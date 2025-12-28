"""
Supabase client service for database operations.
"""

from supabase import create_client, Client
from functools import lru_cache
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache()
def get_supabase_client() -> Client:
    """
    Get cached Supabase client instance.

    Returns:
        Supabase client with service role key (bypasses RLS for server operations)
    """
    try:
        supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_secret_key  # Use secret key for server-side operations
        )
        logger.info("✓ Supabase client initialized")
        return supabase
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        raise


# Singleton instance
supabase_client = get_supabase_client()
