import csv
import os
from datetime import datetime
from typing import List
import logging

from app.core.config import get_settings
from app.models.schemas import VideoData, CSVLogEntry

logger = logging.getLogger(__name__)
settings = get_settings()


class DataService:
    """Service for CSV data operations."""

    def __init__(self):
        """Initialize data service and ensure data directory exists."""
        os.makedirs(settings.data_dir, exist_ok=True)

    def log_videos_to_csv(
        self,
        videos: List[VideoData],
        persona: str,
        channel_handles: dict
    ) -> int:
        """
        Log all fetched videos to competitor_data.csv.

        As per spec.md: "Append every single fetched video to competitor_data.csv"

        Args:
            videos: List of VideoData objects
            persona: The target viewer persona text
            channel_handles: Dict mapping channel_id to handle

        Returns:
            Number of videos logged
        """
        if not videos:
            logger.warning("No videos to log")
            return 0

        file_exists = os.path.exists(settings.csv_file)

        try:
            with open(settings.csv_file, 'a', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'timestamp',
                    'persona',
                    'channel_handle',
                    'channel_id',
                    'video_id',
                    'title',
                    'views',
                    'published_at',
                    'thumbnail_url',
                    'duration_seconds'
                ]

                writer = csv.DictWriter(f, fieldnames=fieldnames)

                # Write header if file doesn't exist
                if not file_exists:
                    writer.writeheader()

                # Log each video
                timestamp = datetime.now()
                for video in videos:
                    # Get channel handle from mapping
                    channel_handle = channel_handles.get(
                        video.channel_id,
                        video.channel_name
                    )

                    entry = CSVLogEntry(
                        timestamp=timestamp,
                        persona=persona,
                        channel_handle=channel_handle,
                        channel_id=video.channel_id,
                        video_id=video.video_id,
                        title=video.title,
                        views=video.view_count,
                        published_at=video.published_at,
                        thumbnail_url=video.thumbnail_url,
                        duration_seconds=video.duration_seconds
                    )

                    writer.writerow(entry.to_dict())

            logger.info(f"✓ Logged {len(videos)} videos to {settings.csv_file}")
            return len(videos)

        except Exception as e:
            logger.error(f"Error logging videos to CSV: {e}")
            return 0

    def get_csv_stats(self) -> dict:
        """
        Get statistics about the CSV file.

        Returns:
            Dict with stats (total rows, file size, etc.)
        """
        if not os.path.exists(settings.csv_file):
            return {
                'exists': False,
                'total_rows': 0,
                'file_size': 0
            }

        try:
            with open(settings.csv_file, 'r', encoding='utf-8') as f:
                row_count = sum(1 for _ in csv.reader(f)) - 1  # Subtract header

            file_size = os.path.getsize(settings.csv_file)

            return {
                'exists': True,
                'total_rows': row_count,
                'file_size': file_size,
                'file_path': settings.csv_file
            }
        except Exception as e:
            logger.error(f"Error getting CSV stats: {e}")
            return {
                'exists': True,
                'total_rows': 0,
                'file_size': 0,
                'error': str(e)
            }
