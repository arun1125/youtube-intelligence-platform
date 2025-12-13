from googleapiclient.discovery import build
from typing import List, Optional, Dict
import logging

from app.config import get_settings
from app.models.schemas import VideoData
from app.utils.helpers import parse_iso_duration

logger = logging.getLogger(__name__)
settings = get_settings()


class YouTubeService:
    """Service for YouTube Data API interactions."""

    def __init__(self):
        """Initialize YouTube API client."""
        self.youtube = build('youtube', 'v3', developerKey=settings.google_api_key)

    def get_channel_info(self, channel_id: str) -> Optional[Dict]:
        """
        Get channel information from YouTube API.

        Args:
            channel_id: YouTube channel ID (UC...)

        Returns:
            Dict with channel info or None if not found
        """
        try:
            response = self.youtube.channels().list(
                part='snippet,contentDetails',
                id=channel_id
            ).execute()

            if 'items' in response and len(response['items']) > 0:
                item = response['items'][0]
                return {
                    'channel_id': channel_id,
                    'title': item['snippet']['title'],
                    'thumbnail': item['snippet']['thumbnails']['default']['url'],
                    'uploads_playlist': item['contentDetails']['relatedPlaylists']['uploads']
                }
        except Exception as e:
            logger.error(f"Error fetching channel info for {channel_id}: {e}")

        return None

    def get_recent_videos(
        self,
        channel_id: str,
        channel_name: str,
        max_results: int = 5
    ) -> List[VideoData]:
        """
        Fetch recent videos from a channel.

        Args:
            channel_id: YouTube channel ID
            channel_name: Channel name/handle
            max_results: Number of videos to fetch (default: 5)

        Returns:
            List of VideoData objects
        """
        logger.info(f"Fetching {max_results} recent videos from {channel_name}")

        videos = []

        try:
            # Step 1: Get uploads playlist ID
            channel_info = self.get_channel_info(channel_id)
            if not channel_info:
                logger.warning(f"Could not get channel info for {channel_id}")
                return videos

            uploads_playlist = channel_info['uploads_playlist']

            # Step 2: Get recent videos from uploads playlist
            playlist_response = self.youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=uploads_playlist,
                maxResults=max_results
            ).execute()

            video_ids = []
            video_metadata = {}

            for item in playlist_response.get('items', []):
                video_id = item['contentDetails']['videoId']
                video_ids.append(video_id)
                video_metadata[video_id] = {
                    'title': item['snippet']['title'],
                    'published_at': item['contentDetails'].get(
                        'videoPublishedAt',
                        item['snippet']['publishedAt']
                    ),
                    'thumbnail_url': self._get_best_thumbnail(item['snippet']['thumbnails'])
                }

            # Step 3: Get video details (duration, views, etc.)
            if video_ids:
                videos_response = self.youtube.videos().list(
                    part='contentDetails,statistics',
                    id=','.join(video_ids)
                ).execute()

                for item in videos_response.get('items', []):
                    video_id = item['id']
                    meta = video_metadata.get(video_id, {})

                    duration_iso = item['contentDetails']['duration']
                    duration_seconds = parse_iso_duration(duration_iso)

                    view_count = int(item['statistics'].get('viewCount', 0))

                    video_data = VideoData(
                        video_id=video_id,
                        title=meta.get('title', 'Untitled'),
                        channel_name=channel_name,
                        channel_id=channel_id,
                        thumbnail_url=meta.get('thumbnail_url', ''),
                        view_count=view_count,
                        published_at=meta.get('published_at', ''),
                        duration_seconds=duration_seconds,
                        video_url=f"https://www.youtube.com/watch?v={video_id}"
                    )

                    videos.append(video_data)

            logger.info(f"✓ Fetched {len(videos)} videos from {channel_name}")

        except Exception as e:
            logger.error(f"Error fetching videos from {channel_name}: {e}")

        return videos

    def _get_best_thumbnail(self, thumbnails: Dict) -> str:
        """
        Get the best quality thumbnail URL.

        Priority: maxres > high > medium > default
        """
        for quality in ['maxres', 'high', 'medium', 'default']:
            if quality in thumbnails:
                return thumbnails[quality]['url']

        return ''

    def get_videos_for_channels(
        self,
        channel_data: List[Dict],
        videos_per_channel: int = 5
    ) -> List[VideoData]:
        """
        Fetch recent videos from multiple channels.

        Args:
            channel_data: List of dicts with 'channel_id' and 'handle'
            videos_per_channel: Number of videos to fetch per channel

        Returns:
            List of all VideoData objects
        """
        all_videos = []

        for channel in channel_data:
            if not channel.get('success'):
                continue

            channel_id = channel['channel_id']
            handle = channel['handle']

            videos = self.get_recent_videos(
                channel_id=channel_id,
                channel_name=handle,
                max_results=videos_per_channel
            )

            all_videos.extend(videos)

        logger.info(f"✓ Total videos fetched: {len(all_videos)}")
        return all_videos
