"""
Viral Video Service

Handles scraping, storing, and retrieving YouTube video data for viral analysis.
"""
from typing import List, Optional, Dict
import logging
from datetime import datetime, timedelta, timezone

from app.core.database import get_supabase_client
from app.features.thumbnail.youtube_service import YouTubeService
from app.utils.channel_resolver import get_channel_id_from_html
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ViralVideoService:
    """Service for managing viral video data."""

    def __init__(self):
        """Initialize the viral video service."""
        self.supabase = get_supabase_client()
        self.youtube = YouTubeService()

    def calculate_view_bucket(self, view_count: int) -> str:
        """
        Calculate the view bucket for a video.

        Args:
            view_count: Number of views

        Returns:
            Bucket string: '5-10k', '10-50k', '50-100k', '100k-1M', '1M+'
        """
        if view_count >= 1_000_000:
            return '1M+'
        elif view_count >= 100_000:
            return '100k-1M'
        elif view_count >= 50_000:
            return '50-100k'
        elif view_count >= 10_000:
            return '10-50k'
        elif view_count >= 5_000:
            return '5-10k'
        else:
            return 'under-5k'

    def check_channel_exists(self, channel_id: str) -> bool:
        """
        Check if channel has already been scraped.

        Args:
            channel_id: YouTube channel ID

        Returns:
            True if channel exists in database, False otherwise
        """
        try:
            response = self.supabase.table('viral_videos').select('id').eq('channel_id', channel_id).limit(1).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking channel existence: {e}")
            return False

    def get_channel_last_scraped(self, channel_id: str) -> Optional[datetime]:
        """
        Get the last scrape date for a channel.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Datetime of last scrape or None
        """
        try:
            response = (
                self.supabase.table('viral_videos')
                .select('scraped_at')
                .eq('channel_id', channel_id)
                .order('scraped_at', desc=True)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return datetime.fromisoformat(response.data[0]['scraped_at'].replace('Z', '+00:00'))
            return None

        except Exception as e:
            logger.error(f"Error getting last scrape date: {e}")
            return None

    def scrape_channel(self, channel_input: str, days: int = 365, force_refresh: bool = False) -> Dict:
        """
        Scrape a YouTube channel and store videos in database.

        Args:
            channel_input: Channel handle (e.g., '@MrBeast') or channel ID
            days: Number of days to look back (default: 365)
            force_refresh: Force re-scraping even if channel exists

        Returns:
            Dict with status and results:
            {
                'success': bool,
                'channel_id': str,
                'channel_name': str,
                'videos_scraped': int,
                'videos_stored': int,
                'already_existed': bool,
                'last_scraped': datetime or None
            }
        """
        result = {
            'success': False,
            'channel_id': None,
            'channel_name': None,
            'videos_scraped': 0,
            'videos_stored': 0,
            'already_existed': False,
            'last_scraped': None,
            'error': None
        }

        try:
            # Step 1: Resolve channel input to channel ID
            if channel_input.startswith('UC') and len(channel_input) == 24:
                # Already a channel ID
                channel_id = channel_input
                logger.info(f"Using provided channel ID: {channel_id}")
            else:
                # Resolve handle to ID
                channel_id, url = get_channel_id_from_html(channel_input)
                if not channel_id:
                    result['error'] = f"Could not resolve channel: {channel_input}"
                    logger.error(result['error'])
                    return result

            result['channel_id'] = channel_id

            # Step 2: Check if channel already exists
            exists = self.check_channel_exists(channel_id)
            last_scraped = self.get_channel_last_scraped(channel_id)

            if exists and not force_refresh:
                result['already_existed'] = True
                result['last_scraped'] = last_scraped
                result['success'] = True
                logger.info(f"Channel {channel_id} already scraped on {last_scraped}")
                return result

            # Step 3: Get channel info
            channel_info = self.youtube.get_channel_info(channel_id)
            if not channel_info:
                result['error'] = f"Could not fetch channel info for {channel_id}"
                logger.error(result['error'])
                return result

            channel_name = channel_info['title']
            result['channel_name'] = channel_name

            # Step 4: Fetch videos from last N days
            # Use timezone-aware UTC datetime for comparison
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            max_videos = settings.max_videos_per_channel

            logger.info(f"Fetching up to {max_videos} videos from {channel_name} (last {days} days)")

            # Fetch videos (we'll get all we can up to max_videos)
            all_videos = self.youtube.get_recent_videos(
                channel_id=channel_id,
                channel_name=channel_name,
                max_results=max_videos
            )

            logger.info(f"Fetched {len(all_videos)} total videos from YouTube")

            # Step 5: Filter videos
            # - Must be >= 5 minutes (300 seconds)
            # - Must be within date range
            filtered_videos = []
            for video in all_videos:
                # Check duration
                if video.duration_seconds < settings.video_min_duration:
                    continue

                # Check date
                pub_date = datetime.fromisoformat(video.published_at.replace('Z', '+00:00'))
                if pub_date < cutoff_date:
                    continue

                filtered_videos.append(video)

            # Set scraped count to filtered videos (videos that match criteria)
            result['videos_scraped'] = len(filtered_videos)
            logger.info(f"Filtered to {len(filtered_videos)} videos (>={settings.video_min_duration}s, within {days} days)")

            # Step 6: Store videos in database
            stored_count = 0
            for video in filtered_videos:
                try:
                    bucket = self.calculate_view_bucket(video.view_count)

                    video_data = {
                        'video_id': video.video_id,
                        'channel_id': channel_id,
                        'channel_name': channel_name,
                        'title': video.title,
                        'thumbnail_url': video.thumbnail_url,
                        'view_count': video.view_count,
                        'duration_seconds': video.duration_seconds,
                        'published_at': video.published_at,
                        'video_url': video.video_url,
                        'view_bucket': bucket,
                        'scraped_at': datetime.now().isoformat()
                    }

                    # Upsert (insert or update if video_id exists)
                    response = (
                        self.supabase.table('viral_videos')
                        .upsert(video_data, on_conflict='video_id')
                        .execute()
                    )

                    stored_count += 1

                except Exception as e:
                    logger.error(f"Error storing video {video.video_id}: {e}")
                    continue

            result['videos_stored'] = stored_count
            result['success'] = True
            logger.info(f"✓ Stored {stored_count} videos from {channel_name}")

            return result

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error scraping channel: {e}")
            return result

    def get_videos_by_bucket(self, channel_id: Optional[str] = None, bucket: Optional[str] = None) -> List[Dict]:
        """
        Get videos filtered by channel and/or bucket.

        Args:
            channel_id: Filter by channel ID (optional)
            bucket: Filter by view bucket (optional)

        Returns:
            List of video dicts
        """
        try:
            query = self.supabase.table('viral_videos').select('*')

            if channel_id:
                query = query.eq('channel_id', channel_id)

            if bucket:
                query = query.eq('view_bucket', bucket)

            # Order by view count descending
            query = query.order('view_count', desc=True)

            response = query.execute()
            return response.data

        except Exception as e:
            logger.error(f"Error fetching videos: {e}")
            return []

    def get_video_details(self, video_id: str) -> Optional[Dict]:
        """
        Get full details for a single video.

        Args:
            video_id: YouTube video ID

        Returns:
            Video dict or None if not found
        """
        try:
            response = self.supabase.table('viral_videos').select('*').eq('video_id', video_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error fetching video details: {e}")
            return None

    def get_bucket_stats(self, channel_id: Optional[str] = None) -> Dict[str, int]:
        """
        Get video count by bucket.

        Args:
            channel_id: Filter by channel ID (optional)

        Returns:
            Dict mapping bucket names to counts
        """
        try:
            query = self.supabase.table('viral_videos').select('view_bucket')

            if channel_id:
                query = query.eq('channel_id', channel_id)

            response = query.execute()

            # Count videos per bucket
            bucket_counts = {
                '1M+': 0,
                '100k-1M': 0,
                '50-100k': 0,
                '10-50k': 0,
                '5-10k': 0,
                'under-5k': 0
            }

            for video in response.data:
                bucket = video.get('view_bucket', 'under-5k')
                if bucket in bucket_counts:
                    bucket_counts[bucket] += 1

            return bucket_counts

        except Exception as e:
            logger.error(f"Error getting bucket stats: {e}")
            return {}

    def get_all_channels(self) -> List[Dict]:
        """
        Get list of all unique channels in the database.

        Returns:
            List of dicts with channel_id and channel_name
        """
        try:
            response = (
                self.supabase.table('viral_videos')
                .select('channel_id, channel_name')
                .execute()
            )

            # Get unique channels
            channels = {}
            for video in response.data:
                channel_id = video['channel_id']
                if channel_id not in channels:
                    channels[channel_id] = {
                        'channel_id': channel_id,
                        'channel_name': video['channel_name']
                    }

            return list(channels.values())

        except Exception as e:
            logger.error(f"Error fetching channels: {e}")
            return []
