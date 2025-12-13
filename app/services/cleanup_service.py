"""
Thumbnail cleanup service - deletes files older than 24 hours.
"""

import os
import time
from pathlib import Path
from datetime import datetime, timedelta
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CleanupService:
    """Service for cleaning up old thumbnail files."""

    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)

    def delete_old_thumbnails(self, max_age_hours: int = 24) -> dict:
        """
        Delete thumbnail files older than specified hours.

        Args:
            max_age_hours: Maximum age in hours (default: 24)

        Returns:
            Dict with cleanup stats
        """
        if not self.upload_dir.exists():
            logger.warning(f"Upload directory does not exist: {self.upload_dir}")
            return {
                'deleted_count': 0,
                'freed_space_mb': 0,
                'error': 'Upload directory not found'
            }

        cutoff_time = time.time() - (max_age_hours * 3600)
        deleted_count = 0
        freed_space = 0

        logger.info(f"🧹 Starting cleanup: deleting files older than {max_age_hours}h")

        try:
            for file_path in self.upload_dir.iterdir():
                if not file_path.is_file():
                    continue

                # Check file age
                file_mtime = file_path.stat().st_mtime

                if file_mtime < cutoff_time:
                    # File is older than cutoff
                    file_size = file_path.stat().st_size
                    freed_space += file_size

                    logger.info(f"  Deleting: {file_path.name} ({self._format_size(file_size)})")

                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"  Failed to delete {file_path.name}: {e}")

            freed_space_mb = freed_space / (1024 * 1024)

            logger.info(f"✅ Cleanup complete: {deleted_count} files deleted, {freed_space_mb:.2f}MB freed")

            return {
                'deleted_count': deleted_count,
                'freed_space_mb': round(freed_space_mb, 2),
                'cleaned_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {
                'deleted_count': 0,
                'freed_space_mb': 0,
                'error': str(e)
            }

    def get_upload_stats(self) -> dict:
        """
        Get statistics about upload directory.

        Returns:
            Dict with file count and total size
        """
        if not self.upload_dir.exists():
            return {
                'file_count': 0,
                'total_size_mb': 0
            }

        file_count = 0
        total_size = 0

        for file_path in self.upload_dir.iterdir():
            if file_path.is_file():
                file_count += 1
                total_size += file_path.stat().st_size

        return {
            'file_count': file_count,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }

    def _format_size(self, size_bytes: int) -> str:
        """Format file size for human readability."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"


# Singleton instance
cleanup_service = CleanupService()
