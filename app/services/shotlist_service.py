"""
Shot List service for video production planning.
Handles CRUD operations for projects, videos, and shots.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.services.supabase_client import supabase_client
from app.models.database import (
    ProductionProject,
    ProductionProjectCreate,
    ProductionVideo,
    ProductionVideoCreate,
    ProductionShot,
    ProductionShotCreate,
)

logger = logging.getLogger(__name__)


class ShotListService:
    """Service for managing production projects, videos, and shots."""

    def __init__(self):
        self.supabase = supabase_client

    # ============================================
    # PROJECT OPERATIONS
    # ============================================

    def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all projects for a user."""
        try:
            response = self.supabase.table("production_projects")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to fetch projects for user {user_id}: {e}")
            raise

    def create_project(self, user_id: str, project_data: ProductionProjectCreate) -> Dict[str, Any]:
        """Create a new project."""
        try:
            response = self.supabase.table("production_projects")\
                .insert({
                    "user_id": user_id,
                    "name": project_data.name,
                    "description": project_data.description,
                })\
                .execute()
            return response.data[0]
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise

    def delete_project(self, user_id: str, project_id: str) -> None:
        """Delete a project (cascades to videos and shots)."""
        try:
            # RLS policy ensures user can only delete their own projects
            self.supabase.table("production_projects")\
                .delete()\
                .eq("id", project_id)\
                .eq("user_id", user_id)\
                .execute()
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}")
            raise

    # ============================================
    # VIDEO OPERATIONS
    # ============================================

    def get_user_videos(self, user_id: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all videos for a user, optionally filtered by project."""
        try:
            query = self.supabase.table("production_videos")\
                .select("*")\
                .eq("user_id", user_id)

            if project_id:
                query = query.eq("project_id", project_id)

            response = query.order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to fetch videos for user {user_id}: {e}")
            raise

    def get_video_by_id(self, user_id: str, video_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific video by ID."""
        try:
            response = self.supabase.table("production_videos")\
                .select("*")\
                .eq("id", video_id)\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to fetch video {video_id}: {e}")
            return None

    def create_video(self, user_id: str, video_data: ProductionVideoCreate) -> Dict[str, Any]:
        """Create a new video."""
        try:
            response = self.supabase.table("production_videos")\
                .insert({
                    "user_id": user_id,
                    "title": video_data.title,
                    "project_id": str(video_data.project_id) if video_data.project_id else None,
                    "idea": video_data.idea,
                })\
                .execute()
            return response.data[0]
        except Exception as e:
            logger.error(f"Failed to create video: {e}")
            raise

    def update_video(self, user_id: str, video_id: str, field: str, value: Any) -> Dict[str, Any]:
        """Update a specific field of a video."""
        try:
            response = self.supabase.table("production_videos")\
                .update({field: value})\
                .eq("id", video_id)\
                .eq("user_id", user_id)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to update video {video_id}: {e}")
            raise

    def delete_video(self, user_id: str, video_id: str) -> None:
        """Delete a video (cascades to shots)."""
        try:
            self.supabase.table("production_videos")\
                .delete()\
                .eq("id", video_id)\
                .eq("user_id", user_id)\
                .execute()
        except Exception as e:
            logger.error(f"Failed to delete video {video_id}: {e}")
            raise

    # ============================================
    # SHOT OPERATIONS
    # ============================================

    def get_video_shots(self, video_id: str) -> List[Dict[str, Any]]:
        """Get all shots for a video, ordered by position."""
        try:
            response = self.supabase.table("production_shots")\
                .select("*")\
                .eq("video_id", video_id)\
                .order("order_index")\
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to fetch shots for video {video_id}: {e}")
            raise

    def create_shot(self, shot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new shot."""
        try:
            response = self.supabase.table("production_shots")\
                .insert(shot_data)\
                .execute()
            return response.data[0]
        except Exception as e:
            logger.error(f"Failed to create shot: {e}")
            raise

    def update_shot(self, shot_id: str, field: str, value: Any) -> Dict[str, Any]:
        """Update a specific field of a shot."""
        try:
            response = self.supabase.table("production_shots")\
                .update({field: value})\
                .eq("id", shot_id)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to update shot {shot_id}: {e}")
            raise

    def delete_shot(self, shot_id: str) -> None:
        """Delete a shot."""
        try:
            self.supabase.table("production_shots")\
                .delete()\
                .eq("id", shot_id)\
                .execute()
        except Exception as e:
            logger.error(f"Failed to delete shot {shot_id}: {e}")
            raise

    def reorder_shots(self, shot_ids: List[str]) -> None:
        """Reorder shots by updating their order_index."""
        try:
            for index, shot_id in enumerate(shot_ids):
                self.supabase.table("production_shots")\
                    .update({"order_index": index})\
                    .eq("id", shot_id)\
                    .execute()
        except Exception as e:
            logger.error(f"Failed to reorder shots: {e}")
            raise


# Singleton instance
shotlist_service = ShotListService()
