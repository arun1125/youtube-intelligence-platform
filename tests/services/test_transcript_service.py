"""
Tests for TranscriptService
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.transcript_service import TranscriptService


class TestTranscriptService:
    """Test suite for TranscriptService."""

    @pytest.fixture
    def service(self, mock_supabase, mock_apify_client, mock_settings):
        """Create service instance with mocked dependencies."""
        with patch('app.services.transcript_service.get_supabase_client', return_value=mock_supabase), \
             patch('app.services.transcript_service.ApifyClient', return_value=mock_apify_client), \
             patch('app.services.transcript_service.settings', mock_settings):
            return TranscriptService()

    def test_get_transcript_from_db_found(self, service, mock_supabase):
        """Test getting transcript from database when it exists."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[{
            'transcript': 'Test transcript text',
            'transcript_fetched_at': '2024-01-01T10:00:00Z'
        }])

        # Act
        result = service.get_transcript_from_db('test_video_123')

        # Assert
        assert result == 'Test transcript text'

    def test_get_transcript_from_db_not_found(self, service, mock_supabase):
        """Test getting transcript from database when it doesn't exist."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[{
            'transcript': None,
            'transcript_fetched_at': None
        }])

        # Act
        result = service.get_transcript_from_db('test_video_123')

        # Assert
        assert result is None

    def test_fetch_transcript_from_apify_success(self, service, mock_apify_client, mock_transcript_response):
        """Test successful transcript fetching from Apify."""
        # Arrange
        mock_apify_client.iterate_items.return_value = [mock_transcript_response]

        # Act
        result = service.fetch_transcript_from_apify('test_video_123')

        # Assert
        assert result is not None
        assert 'This is the first part' in result
        assert 'final part of the video' in result

    def test_fetch_transcript_from_apify_failure(self, service, mock_apify_client):
        """Test transcript fetching failure from Apify."""
        # Arrange
        mock_apify_client.iterate_items.return_value = []

        # Act
        result = service.fetch_transcript_from_apify('test_video_123')

        # Assert
        assert result is None

    def test_save_transcript_success(self, service, mock_supabase):
        """Test saving transcript to database."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[{'id': 1}])

        # Act
        result = service.save_transcript('test_video_123', 'Test transcript')

        # Assert
        assert result is True
        mock_supabase.update.assert_called_once()

    def test_fetch_transcript_uses_cached(self, service, mock_supabase):
        """Test fetch_transcript uses cached version."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[{
            'transcript': 'Cached transcript',
            'transcript_fetched_at': '2024-01-01T10:00:00Z'
        }])

        # Act
        result = service.fetch_transcript('test_video_123', force_refresh=False)

        # Assert
        assert result == 'Cached transcript'

    def test_fetch_transcript_force_refresh(self, service, mock_supabase, mock_apify_client, mock_transcript_response):
        """Test fetch_transcript with force refresh."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[{'id': 1}])
        mock_apify_client.iterate_items.return_value = [mock_transcript_response]

        # Act
        result = service.fetch_transcript('test_video_123', force_refresh=True)

        # Assert
        assert result is not None
        mock_apify_client.actor.assert_called()

    def test_bulk_fetch_transcripts(self, service, mock_supabase, mock_apify_client, mock_transcript_response):
        """Test bulk fetching of transcripts."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[])
        mock_apify_client.iterate_items.return_value = [mock_transcript_response]

        video_ids = ['video1', 'video2', 'video3']

        # Act
        result = service.bulk_fetch_transcripts(video_ids)

        # Assert
        assert len(result) == 3
        assert 'video1' in result
        assert 'video2' in result
        assert 'video3' in result

    def test_get_transcript_summary(self, service):
        """Test transcript summary generation."""
        # Arrange
        long_transcript = ' '.join(['word'] * 1000)

        # Act
        result = service.get_transcript_summary(long_transcript, max_words=100)

        # Assert
        assert len(result.split()) <= 101  # 100 words + '...'
        assert result.endswith('...')

    def test_get_transcript_summary_short_text(self, service):
        """Test transcript summary with short text."""
        # Arrange
        short_transcript = 'This is a short transcript'

        # Act
        result = service.get_transcript_summary(short_transcript, max_words=100)

        # Assert
        assert result == short_transcript
        assert not result.endswith('...')
