"""
Tests for ViralVideoService
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from app.services.viral_video_service import ViralVideoService


class TestViralVideoService:
    """Test suite for ViralVideoService."""

    @pytest.fixture
    def service(self, mock_supabase, mock_youtube_service):
        """Create service instance with mocked dependencies."""
        with patch('app.services.viral_video_service.get_supabase_client', return_value=mock_supabase), \
             patch('app.services.viral_video_service.YouTubeService', return_value=mock_youtube_service):
            return ViralVideoService()

    def test_calculate_view_bucket_1m_plus(self, service):
        """Test view bucket calculation for 1M+ views."""
        assert service.calculate_view_bucket(1_500_000) == '1M+'

    def test_calculate_view_bucket_100k_1m(self, service):
        """Test view bucket calculation for 100k-1M views."""
        assert service.calculate_view_bucket(500_000) == '100k-1M'

    def test_calculate_view_bucket_50_100k(self, service):
        """Test view bucket calculation for 50-100k views."""
        assert service.calculate_view_bucket(75_000) == '50-100k'

    def test_calculate_view_bucket_10_50k(self, service):
        """Test view bucket calculation for 10-50k views."""
        assert service.calculate_view_bucket(25_000) == '10-50k'

    def test_calculate_view_bucket_5_10k(self, service):
        """Test view bucket calculation for 5-10k views."""
        assert service.calculate_view_bucket(7_500) == '5-10k'

    def test_calculate_view_bucket_under_5k(self, service):
        """Test view bucket calculation for under 5k views."""
        assert service.calculate_view_bucket(2_000) == 'under-5k'

    def test_check_channel_exists_returns_true(self, service, mock_supabase):
        """Test check_channel_exists when channel exists."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[{'id': 1}])

        # Act
        result = service.check_channel_exists('UC123456789')

        # Assert
        assert result is True

    def test_check_channel_exists_returns_false(self, service, mock_supabase):
        """Test check_channel_exists when channel doesn't exist."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[])

        # Act
        result = service.check_channel_exists('UC987654321')

        # Assert
        assert result is False

    def test_get_channel_last_scraped(self, service, mock_supabase):
        """Test getting last scrape date for channel."""
        # Arrange
        scraped_date = datetime.now().isoformat()
        mock_supabase.execute.return_value = Mock(data=[{'scraped_at': scraped_date}])

        # Act
        result = service.get_channel_last_scraped('UC123456789')

        # Assert
        assert result is not None
        assert isinstance(result, datetime)

    @patch('app.services.viral_video_service.get_channel_id_from_html')
    def test_scrape_channel_success(self, mock_resolve, service, mock_supabase, mock_youtube_service):
        """Test successful channel scraping."""
        # Arrange
        mock_resolve.return_value = ('UC123456789', 'https://youtube.com/c/test')
        mock_supabase.execute.return_value = Mock(data=[])  # Channel doesn't exist

        # Mock VideoData objects
        mock_video = Mock()
        mock_video.video_id = 'test123'
        mock_video.title = 'Test Video'
        mock_video.view_count = 50000
        mock_video.duration_seconds = 600
        mock_video.published_at = datetime.now().isoformat()
        mock_video.thumbnail_url = 'https://example.com/thumb.jpg'
        mock_video.video_url = 'https://youtube.com/watch?v=test123'

        mock_youtube_service.get_recent_videos.return_value = [mock_video]

        # Act
        result = service.scrape_channel('@TestChannel')

        # Assert
        assert result['success'] is True
        assert result['channel_id'] == 'UC123456789'
        assert result['videos_scraped'] == 1

    def test_scrape_channel_already_exists(self, service, mock_supabase):
        """Test scraping when channel already exists."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[{'id': 1}])  # Channel exists

        # Act
        result = service.scrape_channel('UC123456789', force_refresh=False)

        # Assert
        assert result['success'] is True
        assert result['already_existed'] is True

    def test_get_videos_by_bucket(self, service, mock_supabase, mock_video_data):
        """Test getting videos filtered by bucket."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[mock_video_data])

        # Act
        result = service.get_videos_by_bucket(channel_id='UC123', bucket='100k-1M')

        # Assert
        assert len(result) == 1
        assert result[0]['video_id'] == 'dQw4w9WgXcQ'

    def test_get_video_details(self, service, mock_supabase, mock_video_data):
        """Test getting single video details."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[mock_video_data])

        # Act
        result = service.get_video_details('dQw4w9WgXcQ')

        # Assert
        assert result is not None
        assert result['video_id'] == 'dQw4w9WgXcQ'
        assert result['title'] == 'How to Build a Viral App'

    def test_get_video_details_not_found(self, service, mock_supabase):
        """Test getting video details when video not found."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[])

        # Act
        result = service.get_video_details('nonexistent')

        # Assert
        assert result is None

    def test_get_bucket_stats(self, service, mock_supabase):
        """Test getting video counts per bucket."""
        # Arrange
        mock_videos = [
            {'view_bucket': '1M+'},
            {'view_bucket': '1M+'},
            {'view_bucket': '100k-1M'},
            {'view_bucket': '50-100k'},
        ]
        mock_supabase.execute.return_value = Mock(data=mock_videos)

        # Act
        result = service.get_bucket_stats()

        # Assert
        assert result['1M+'] == 2
        assert result['100k-1M'] == 1
        assert result['50-100k'] == 1
        assert result['10-50k'] == 0

    def test_get_all_channels(self, service, mock_supabase):
        """Test getting all unique channels."""
        # Arrange
        mock_videos = [
            {'channel_id': 'UC123', 'channel_name': 'Channel 1'},
            {'channel_id': 'UC123', 'channel_name': 'Channel 1'},
            {'channel_id': 'UC456', 'channel_name': 'Channel 2'},
        ]
        mock_supabase.execute.return_value = Mock(data=mock_videos)

        # Act
        result = service.get_all_channels()

        # Assert
        assert len(result) == 2
        assert any(c['channel_id'] == 'UC123' for c in result)
        assert any(c['channel_id'] == 'UC456' for c in result)
