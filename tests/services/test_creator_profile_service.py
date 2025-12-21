"""
Tests for CreatorProfileService
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.creator_profile_service import CreatorProfileService


class TestCreatorProfileService:
    """Test suite for CreatorProfileService."""

    @pytest.fixture
    def service(self, mock_supabase):
        """Create service instance with mocked Supabase."""
        with patch('app.services.creator_profile_service.get_supabase_client', return_value=mock_supabase):
            return CreatorProfileService()

    def test_profile_exists_returns_true_when_profile_found(self, service, mock_supabase):
        """Test profile_exists returns True when profile is found."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[{'id': 1}])

        # Act
        result = service.profile_exists('user-123')

        # Assert
        assert result is True
        mock_supabase.table.assert_called_with('user_creator_profile')

    def test_profile_exists_returns_false_when_no_profile(self, service, mock_supabase):
        """Test profile_exists returns False when no profile found."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[])

        # Act
        result = service.profile_exists('user-123')

        # Assert
        assert result is False

    def test_get_user_profile_returns_profile_when_found(self, service, mock_supabase, mock_creator_profile):
        """Test get_user_profile returns profile data."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[mock_creator_profile])

        # Act
        result = service.get_user_profile('test-user-123')

        # Assert
        assert result == mock_creator_profile
        assert result['creator_name'] == 'Tech Educator'

    def test_get_user_profile_returns_none_when_not_found(self, service, mock_supabase):
        """Test get_user_profile returns None when profile not found."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[])

        # Act
        result = service.get_user_profile('nonexistent-user')

        # Assert
        assert result is None

    def test_create_profile_success(self, service, mock_supabase, mock_creator_profile):
        """Test successful profile creation."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[mock_creator_profile])

        profile_data = {
            'creator_name': 'Tech Educator',
            'bio': 'I teach programming',
            'niche': 'Technology',
            'expertise_areas': ['Python', 'JavaScript'],
            'tone_preference': 'Educational',
            'target_audience': 'Developers'
        }

        # Act
        result = service.create_profile('test-user-123', profile_data)

        # Assert
        assert result is not None
        assert result['creator_name'] == 'Tech Educator'
        mock_supabase.table.assert_called_with('user_creator_profile')
        mock_supabase.insert.assert_called_once()

    def test_create_profile_failure(self, service, mock_supabase):
        """Test profile creation failure."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[])

        profile_data = {'creator_name': 'Test'}

        # Act
        result = service.create_profile('test-user-123', profile_data)

        # Assert
        assert result is None

    def test_update_profile_success(self, service, mock_supabase, mock_creator_profile):
        """Test successful profile update."""
        # Arrange
        updated_profile = mock_creator_profile.copy()
        updated_profile['creator_name'] = 'Updated Name'
        mock_supabase.execute.return_value = Mock(data=[updated_profile])

        update_data = {'creator_name': 'Updated Name'}

        # Act
        result = service.update_profile('test-user-123', update_data)

        # Assert
        assert result is not None
        assert result['creator_name'] == 'Updated Name'
        mock_supabase.update.assert_called_once()

    def test_delete_profile_success(self, service, mock_supabase):
        """Test successful profile deletion."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[{'id': 1}])

        # Act
        result = service.delete_profile('test-user-123')

        # Assert
        assert result is True
        mock_supabase.delete.assert_called_once()

    def test_get_profile_summary(self, service, mock_supabase, mock_creator_profile):
        """Test profile summary generation."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[mock_creator_profile])

        # Act
        summary = service.get_profile_summary('test-user-123')

        # Assert
        assert 'Tech Educator' in summary
        assert 'Technology Education' in summary
        assert 'Python, JavaScript, AI' in summary
        assert 'Educational' in summary

    def test_get_profile_summary_no_profile(self, service, mock_supabase):
        """Test profile summary when no profile exists."""
        # Arrange
        mock_supabase.execute.return_value = Mock(data=[])

        # Act
        summary = service.get_profile_summary('nonexistent-user')

        # Assert
        assert 'No creator profile available' in summary
