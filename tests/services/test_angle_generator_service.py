"""
Tests for AngleGeneratorService
"""
import pytest
import json
from unittest.mock import Mock, patch
from app.services.angle_generator_service import AngleGeneratorService


class TestAngleGeneratorService:
    """Test suite for AngleGeneratorService."""

    @pytest.fixture
    def service(self, mock_anthropic_client, mock_settings):
        """Create service instance with mocked Claude client."""
        with patch('app.services.angle_generator_service.Anthropic', return_value=mock_anthropic_client), \
             patch('app.services.angle_generator_service.settings', mock_settings):
            return AngleGeneratorService()

    def test_generate_angles_success(self, service, mock_anthropic_client, mock_video_data, mock_creator_profile):
        """Test successful angle generation."""
        # Arrange
        angles_json = json.dumps([
            {
                'angle_name': 'Technical Deep Dive',
                'core_hook': 'Test hook',
                'key_differentiator': 'Test diff',
                'target_emotion': 'curiosity',
                'estimated_appeal': 'high'
            },
            {
                'angle_name': 'Beginner Friendly',
                'core_hook': 'Test hook 2',
                'key_differentiator': 'Test diff 2',
                'target_emotion': 'education',
                'estimated_appeal': 'high'
            },
            {
                'angle_name': 'Contrarian Take',
                'core_hook': 'Test hook 3',
                'key_differentiator': 'Test diff 3',
                'target_emotion': 'controversy',
                'estimated_appeal': 'medium'
            }
        ])

        mock_content = Mock()
        mock_content.text = angles_json
        mock_message = Mock()
        mock_message.content = [mock_content]
        mock_anthropic_client.messages.create.return_value = mock_message

        # Act
        result = service.generate_angles(mock_video_data, mock_creator_profile, 'Test transcript')

        # Assert
        assert len(result) == 3
        assert result[0]['angle_name'] == 'Technical Deep Dive'
        assert result[1]['angle_name'] == 'Beginner Friendly'
        mock_anthropic_client.messages.create.assert_called_once()

    def test_generate_angles_with_markdown_code_blocks(self, service, mock_anthropic_client, mock_video_data, mock_creator_profile):
        """Test angle generation with markdown code blocks in response."""
        # Arrange
        angles_data = [{
            'angle_name': 'Test Angle',
            'core_hook': 'Test hook',
            'key_differentiator': 'Test diff',
            'target_emotion': 'curiosity',
            'estimated_appeal': 'high'
        }] * 3

        angles_json = f"```json\n{json.dumps(angles_data)}\n```"

        mock_content = Mock()
        mock_content.text = angles_json
        mock_message = Mock()
        mock_message.content = [mock_content]
        mock_anthropic_client.messages.create.return_value = mock_message

        # Act
        result = service.generate_angles(mock_video_data, mock_creator_profile, 'Test transcript')

        # Assert
        assert len(result) == 3

    def test_generate_angles_fallback_on_failure(self, service, mock_anthropic_client, mock_video_data, mock_creator_profile):
        """Test fallback angles when Claude fails."""
        # Arrange
        mock_anthropic_client.messages.create.side_effect = Exception('API Error')

        # Act
        result = service.generate_angles(mock_video_data, mock_creator_profile, 'Test transcript')

        # Assert
        assert len(result) >= 3  # Should return fallback angles
        assert isinstance(result, list)

    def test_parse_angles_response_valid_json(self, service):
        """Test parsing valid JSON response."""
        # Arrange
        angles_data = [
            {'angle_name': 'Test', 'core_hook': 'Hook', 'key_differentiator': 'Diff'}
        ] * 3
        response_text = json.dumps(angles_data)

        # Act
        result = service._parse_angles_response(response_text)

        # Assert
        assert len(result) == 3

    def test_parse_angles_response_invalid_json(self, service):
        """Test parsing invalid JSON response."""
        # Arrange
        response_text = "This is not valid JSON"

        # Act
        result = service._parse_angles_response(response_text)

        # Assert
        assert result == []

    def test_parse_angles_response_max_5_angles(self, service):
        """Test that only max 5 angles are returned."""
        # Arrange
        angles_data = [
            {'angle_name': f'Angle {i}', 'core_hook': 'Hook', 'key_differentiator': 'Diff'}
            for i in range(10)
        ]
        response_text = json.dumps(angles_data)

        # Act
        result = service._parse_angles_response(response_text)

        # Assert
        assert len(result) <= 5

    def test_format_angle_for_display(self, service, mock_angle):
        """Test formatting angle for display."""
        # Act
        result = service.format_angle_for_display(mock_angle)

        # Assert
        assert 'Technical Deep Dive' in result
        assert 'Everyone talks about the results' in result
        assert 'curiosity' in result
