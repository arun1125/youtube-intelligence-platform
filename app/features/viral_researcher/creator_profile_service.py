"""
Creator Profile Service

Handles user creator profile operations for the Viral Researcher & Scripter module.
"""
from typing import Optional, Dict
import logging
from datetime import datetime

from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)


class CreatorProfileService:
    """Service for managing user creator profiles."""

    def __init__(self):
        """Initialize the creator profile service."""
        self.supabase = get_supabase_client()

    def profile_exists(self, user_id: str) -> bool:
        """Check if user has a creator profile."""
        try:
            # Check if user_creator_profile table is correct
            response = self.supabase.table('user_creator_profile').select('id').eq('user_id', user_id).limit(1).execute()
            exists = len(response.data) > 0
            logger.info(f"Profile check for {user_id} in 'user_creator_profile': {exists}")
            return exists
        except Exception as e:
            logger.error(f"Error checking profile existence: {e}")
            return False

    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """
        Get the creator profile for a user.

        Args:
            user_id: UUID of the user

        Returns:
            Dict with profile data or None if not found
        """
        try:
            response = self.supabase.table('user_creator_profile').select('*').eq('user_id', user_id).execute()

            if response.data and len(response.data) > 0:
                profile = response.data[0]
                logger.info(f"✓ Retrieved profile for user {user_id}")
                return profile
            else:
                logger.info(f"No profile found for user {user_id}")
                return None

        except Exception as e:
            logger.error(f"Error fetching profile for user {user_id}: {e}")
            return None

    def create_profile(self, user_id: str, profile_data: Dict) -> Optional[Dict]:
        """
        Create a new creator profile for a user.

        Args:
            user_id: UUID of the user
            profile_data: Dict with profile fields:
                - creator_name: str
                - bio: str
                - niche: str
                - expertise_areas: List[str]
                - tone_preference: str
                - target_audience: str
                - additional_notes: str (optional)

        Returns:
            Created profile dict or None if failed
        """
        try:
            # Add user_id to the data
            data = {
                'user_id': user_id,
                'creator_name': profile_data.get('creator_name'),
                'bio': profile_data.get('bio'),
                'niche': profile_data.get('niche'),
                'expertise_areas': profile_data.get('expertise_areas', []),
                'tone_preference': profile_data.get('tone_preference'),
                'target_audience': profile_data.get('target_audience'),
                'additional_notes': profile_data.get('additional_notes', '')
            }

            response = self.supabase.table('user_creator_profile').insert(data).execute()

            if response.data and len(response.data) > 0:
                logger.info(f"✓ Created profile for user {user_id}")
                return response.data[0]
            else:
                logger.error(f"Failed to create profile for user {user_id}")
                return None

        except Exception as e:
            logger.error(f"Error creating profile for user {user_id}: {e}")
            return None

    def update_profile(self, user_id: str, profile_data: Dict) -> Optional[Dict]:
        """
        Update an existing creator profile.

        Args:
            user_id: UUID of the user
            profile_data: Dict with profile fields to update

        Returns:
            Updated profile dict or None if failed
        """
        try:
            # Filter out None values and user_id
            update_data = {k: v for k, v in profile_data.items() if v is not None and k != 'user_id'}

            response = (
                self.supabase.table('user_creator_profile')
                .update(update_data)
                .eq('user_id', user_id)
                .execute()
            )

            if response.data and len(response.data) > 0:
                logger.info(f"✓ Updated profile for user {user_id}")
                return response.data[0]
            else:
                logger.error(f"Failed to update profile for user {user_id}")
                return None

        except Exception as e:
            logger.error(f"Error updating profile for user {user_id}: {e}")
            return None

    def delete_profile(self, user_id: str) -> bool:
        """
        Delete a creator profile.

        Args:
            user_id: UUID of the user

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            response = self.supabase.table('user_creator_profile').delete().eq('user_id', user_id).execute()

            logger.info(f"✓ Deleted profile for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting profile for user {user_id}: {e}")
            return False

    def get_profile_summary(self, user_id: str) -> str:
        """
        Get a text summary of the creator profile for use in AI prompts.

        Args:
            user_id: UUID of the user

        Returns:
            Formatted string summary of profile
        """
        profile = self.get_user_profile(user_id)

        if not profile:
            return "No creator profile available."

        expertise = ", ".join(profile.get('expertise_areas', []))

        summary = f"""Creator Profile:
- Name: {profile.get('creator_name', 'Not specified')}
- Niche: {profile.get('niche', 'Not specified')}
- Bio: {profile.get('bio', 'Not specified')}
- Expertise: {expertise or 'Not specified'}
- Tone: {profile.get('tone_preference', 'Not specified')}
- Target Audience: {profile.get('target_audience', 'Not specified')}
"""

        if profile.get('additional_notes'):
            summary += f"- Additional Notes: {profile.get('additional_notes')}\n"

        return summary
