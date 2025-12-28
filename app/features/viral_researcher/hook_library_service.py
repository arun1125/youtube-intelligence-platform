"""
Hook Library Service

Manages saved hooks for reuse across scripts.
"""

from typing import List, Optional, Dict
import logging
import re

from app.core.database import get_supabase_client
from app.models.database import HookCategory

logger = logging.getLogger(__name__)


class HookLibraryService:
    """Service for managing the hook library."""

    def __init__(self):
        """Initialize the hook library service."""
        self.supabase = get_supabase_client()

    def save_hook(
        self,
        user_id: str,
        hook_text: str,
        category: str = "other",
        source_script_id: Optional[int] = None,
        source_video_title: Optional[str] = None,
        source_angle: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict:
        """
        Save a hook to the library.

        Args:
            user_id: The user's ID
            hook_text: The hook text to save
            category: Hook category (curiosity, controversy, etc.)
            source_script_id: ID of the script this hook came from
            source_video_title: Title of the source video
            source_angle: The angle that generated this hook
            tags: Optional tags for organization

        Returns:
            The created hook record
        """
        try:
            # Auto-detect category if not provided or is "other"
            if category == "other":
                category = self._detect_category(hook_text)

            hook_data = {
                "user_id": user_id,
                "hook_text": hook_text,
                "category": category,
                "source_script_id": source_script_id,
                "source_video_title": source_video_title,
                "source_angle": source_angle,
                "tags": tags or [],
                "is_favorite": False,
                "use_count": 0
            }

            response = self.supabase.table("hooks").insert(hook_data).execute()

            if response.data and len(response.data) > 0:
                logger.info(f"✓ Saved hook for user {user_id}: {hook_text[:50]}...")
                return response.data[0]
            else:
                raise Exception("Failed to save hook")

        except Exception as e:
            logger.error(f"Error saving hook: {e}")
            raise

    def get_hooks(
        self,
        user_id: str,
        category: Optional[str] = None,
        search: Optional[str] = None,
        favorites_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get hooks from the library with optional filters.

        Args:
            user_id: The user's ID
            category: Filter by category
            search: Search text in hook content
            favorites_only: Only return favorites
            limit: Max results to return
            offset: Pagination offset

        Returns:
            List of hook records
        """
        try:
            query = self.supabase.table("hooks") \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True)

            if category:
                query = query.eq("category", category)

            if favorites_only:
                query = query.eq("is_favorite", True)

            if search:
                query = query.ilike("hook_text", f"%{search}%")

            query = query.range(offset, offset + limit - 1)

            response = query.execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error fetching hooks: {e}")
            return []

    def get_hook(self, user_id: str, hook_id: str) -> Optional[Dict]:
        """
        Get a single hook by ID.

        Args:
            user_id: The user's ID
            hook_id: The hook ID

        Returns:
            The hook record or None
        """
        try:
            response = self.supabase.table("hooks") \
                .select("*") \
                .eq("id", hook_id) \
                .eq("user_id", user_id) \
                .single() \
                .execute()

            return response.data

        except Exception as e:
            logger.error(f"Error fetching hook: {e}")
            return None

    def update_hook(
        self,
        user_id: str,
        hook_id: str,
        hook_text: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_favorite: Optional[bool] = None
    ) -> Optional[Dict]:
        """
        Update a hook.

        Args:
            user_id: The user's ID
            hook_id: The hook ID
            hook_text: New hook text
            category: New category
            tags: New tags
            is_favorite: New favorite status

        Returns:
            The updated hook record or None
        """
        try:
            update_data = {"updated_at": "now()"}

            if hook_text is not None:
                update_data["hook_text"] = hook_text
            if category is not None:
                update_data["category"] = category
            if tags is not None:
                update_data["tags"] = tags
            if is_favorite is not None:
                update_data["is_favorite"] = is_favorite

            response = self.supabase.table("hooks") \
                .update(update_data) \
                .eq("id", hook_id) \
                .eq("user_id", user_id) \
                .execute()

            if response.data and len(response.data) > 0:
                logger.info(f"✓ Updated hook {hook_id}")
                return response.data[0]

            return None

        except Exception as e:
            logger.error(f"Error updating hook: {e}")
            return None

    def delete_hook(self, user_id: str, hook_id: str) -> bool:
        """
        Delete a hook.

        Args:
            user_id: The user's ID
            hook_id: The hook ID

        Returns:
            True if deleted successfully
        """
        try:
            self.supabase.table("hooks") \
                .delete() \
                .eq("id", hook_id) \
                .eq("user_id", user_id) \
                .execute()

            logger.info(f"✓ Deleted hook {hook_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting hook: {e}")
            return False

    def toggle_favorite(self, user_id: str, hook_id: str) -> Optional[Dict]:
        """
        Toggle the favorite status of a hook.

        Args:
            user_id: The user's ID
            hook_id: The hook ID

        Returns:
            The updated hook record or None
        """
        try:
            # Get current status
            hook = self.get_hook(user_id, hook_id)
            if not hook:
                return None

            # Toggle
            new_status = not hook.get("is_favorite", False)

            return self.update_hook(user_id, hook_id, is_favorite=new_status)

        except Exception as e:
            logger.error(f"Error toggling favorite: {e}")
            return None

    def increment_use_count(self, user_id: str, hook_id: str) -> None:
        """
        Increment the use count for a hook.

        Args:
            user_id: The user's ID
            hook_id: The hook ID
        """
        try:
            # Get current count
            hook = self.get_hook(user_id, hook_id)
            if not hook:
                return

            new_count = hook.get("use_count", 0) + 1

            self.supabase.table("hooks") \
                .update({"use_count": new_count, "updated_at": "now()"}) \
                .eq("id", hook_id) \
                .eq("user_id", user_id) \
                .execute()

            logger.debug(f"Incremented use count for hook {hook_id} to {new_count}")

        except Exception as e:
            logger.error(f"Error incrementing use count: {e}")

    def get_categories_with_counts(self, user_id: str) -> Dict[str, int]:
        """
        Get all categories with their hook counts.

        Args:
            user_id: The user's ID

        Returns:
            Dict mapping category name to count
        """
        try:
            response = self.supabase.table("hooks") \
                .select("category") \
                .eq("user_id", user_id) \
                .execute()

            if not response.data:
                return {}

            counts = {}
            for hook in response.data:
                cat = hook.get("category", "other")
                counts[cat] = counts.get(cat, 0) + 1

            return counts

        except Exception as e:
            logger.error(f"Error getting category counts: {e}")
            return {}

    def _detect_category(self, hook_text: str) -> str:
        """
        Auto-detect the category of a hook based on its content.

        Args:
            hook_text: The hook text

        Returns:
            Detected category string
        """
        text_lower = hook_text.lower()

        # Question patterns
        if "?" in hook_text or text_lower.startswith(("what if", "have you", "did you", "why do", "how do")):
            return "question"

        # Statistic patterns
        if re.search(r'\d+%|\d+\s*(million|billion|thousand|percent)', text_lower):
            return "statistic"

        # Shock patterns
        if any(word in text_lower for word in ["shocking", "unbelievable", "insane", "crazy", "mind-blowing", "never believe"]):
            return "shock"

        # Challenge patterns
        if any(word in text_lower for word in ["challenge", "tried", "attempted", "tested", "experiment"]):
            return "challenge"

        # Promise patterns
        if any(word in text_lower for word in ["will show", "going to reveal", "learn how", "discover", "secret"]):
            return "promise"

        # Story patterns
        if any(word in text_lower for word in ["story", "when i", "one day", "happened", "remember when"]):
            return "story"

        # Controversy patterns
        if any(word in text_lower for word in ["wrong", "lie", "truth", "nobody tells", "controversial", "unpopular"]):
            return "controversy"

        # Curiosity patterns
        if any(word in text_lower for word in ["curious", "wonder", "mystery", "strange", "weird", "hidden"]):
            return "curiosity"

        return "other"

    def extract_hook_from_script(self, script: str) -> Optional[str]:
        """
        Extract the hook section from a generated script.

        Args:
            script: The full script text

        Returns:
            The extracted hook text or None
        """
        try:
            # Look for hook section markers
            patterns = [
                r'\[HOOK\](.*?)(?:\[INTRO\]|\[BODY\]|$)',
                r'📌 HOOK.*?━━━━━━━━━━━━━━━━━(.*?)(?:🎬|📝|$)',
                r'HOOK \(0-5 seconds\)(.*?)(?:INTRODUCTION|INTRO|$)'
            ]

            for pattern in patterns:
                match = re.search(pattern, script, re.DOTALL | re.IGNORECASE)
                if match:
                    hook = match.group(1).strip()
                    # Clean up any remaining markers
                    hook = re.sub(r'━+', '', hook).strip()
                    if hook and len(hook) > 10:
                        return hook

            # Fallback: get first 2 sentences
            sentences = re.split(r'[.!?]+', script)
            if len(sentences) >= 2:
                return '. '.join(sentences[:2]).strip() + '.'

            return None

        except Exception as e:
            logger.error(f"Error extracting hook: {e}")
            return None
