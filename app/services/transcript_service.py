"""
Transcript Service

Handles fetching and storing YouTube video transcripts using Apify API.
"""
from typing import Optional
import logging
from datetime import datetime

from apify_client import ApifyClient

from app.services.supabase_client import get_supabase_client
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TranscriptService:
    """Service for managing video transcripts."""

    def __init__(self):
        """Initialize the transcript service."""
        self.supabase = get_supabase_client()
        self.apify = ApifyClient(settings.apify_api_key)

    def get_transcript_from_db(self, video_id: str) -> Optional[str]:
        """
        Get transcript from database if it exists.

        Args:
            video_id: YouTube video ID

        Returns:
            Transcript text or None if not found/not fetched yet
        """
        try:
            response = (
                self.supabase.table('viral_videos')
                .select('transcript, transcript_fetched_at')
                .eq('video_id', video_id)
                .execute()
            )

            if response.data and len(response.data) > 0:
                video = response.data[0]
                transcript = video.get('transcript')

                if transcript:
                    logger.info(f"✓ Retrieved transcript from DB for video {video_id}")
                    return transcript

            return None

        except Exception as e:
            logger.error(f"Error fetching transcript from DB: {e}")
            return None

    def fetch_transcript_from_apify(self, video_id: str) -> Optional[str]:
        """
        Fetch transcript from Apify API.

        Args:
            video_id: YouTube video ID

        Returns:
            Transcript text or None if failed
        """
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            logger.info(f"Fetching transcript via Apify for {video_id}...")

            # Prepare the Actor input
            run_input = {
                "youtube_url": video_url,
                "language": "en"
            }

            # Run the Actor and wait for it to finish
            run = self.apify.actor(settings.apify_transcript_actor).call(run_input=run_input)

            # Fetch results from the run's dataset
            transcript_parts = []
            for item in self.apify.dataset(run["defaultDatasetId"]).iterate_items():
                # Extract transcript from the response
                if 'transcript' in item:
                    transcript_data = item['transcript']

                    # Transcript is a list of segments with 'text' field
                    if isinstance(transcript_data, list):
                        for segment in transcript_data:
                            if 'text' in segment:
                                transcript_parts.append(segment['text'])

            if transcript_parts:
                transcript = ' '.join(transcript_parts)
                logger.info(f"✓ Fetched transcript via Apify ({len(transcript)} chars)")
                return transcript
            else:
                logger.warning(f"No transcript found in Apify response for {video_id}")
                return None

        except Exception as e:
            logger.error(f"Error fetching transcript via Apify: {e}")
            return None

    def save_transcript(self, video_id: str, transcript: str) -> bool:
        """
        Save transcript to database.

        Args:
            video_id: YouTube video ID
            transcript: Transcript text

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            update_data = {
                'transcript': transcript,
                'transcript_fetched_at': datetime.now().isoformat()
            }

            response = (
                self.supabase.table('viral_videos')
                .update(update_data)
                .eq('video_id', video_id)
                .execute()
            )

            logger.info(f"✓ Saved transcript to DB for video {video_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving transcript to DB: {e}")
            return False

    def fetch_transcript(self, video_id: str, force_refresh: bool = False) -> Optional[str]:
        """
        Get transcript for a video (lazy loading).

        First checks database, then fetches via Apify if not found.

        Args:
            video_id: YouTube video ID
            force_refresh: Force re-fetching even if transcript exists

        Returns:
            Transcript text or None if failed
        """
        # Step 1: Check database (unless force refresh)
        if not force_refresh:
            existing_transcript = self.get_transcript_from_db(video_id)
            if existing_transcript:
                return existing_transcript

        # Step 2: Fetch from Apify
        logger.info(f"Transcript not in DB, fetching via Apify for {video_id}")
        transcript = self.fetch_transcript_from_apify(video_id)

        if transcript:
            # Step 3: Save to database
            self.save_transcript(video_id, transcript)
            return transcript
        else:
            logger.error(f"Failed to fetch transcript for {video_id}")
            return None

    def bulk_fetch_transcripts(self, video_ids: list[str]) -> dict[str, Optional[str]]:
        """
        Fetch transcripts for multiple videos.

        Args:
            video_ids: List of YouTube video IDs

        Returns:
            Dict mapping video_id to transcript (or None if failed)
        """
        results = {}

        for video_id in video_ids:
            try:
                transcript = self.fetch_transcript(video_id)
                results[video_id] = transcript
            except Exception as e:
                logger.error(f"Error fetching transcript for {video_id}: {e}")
                results[video_id] = None

        return results

    def get_transcript_summary(self, transcript: str, max_words: int = 500) -> str:
        """
        Get a truncated summary of the transcript.

        Args:
            transcript: Full transcript text
            max_words: Maximum number of words to return

        Returns:
            Truncated transcript
        """
        if not transcript:
            return ""

        words = transcript.split()
        if len(words) <= max_words:
            return transcript

        return ' '.join(words[:max_words]) + '...'
