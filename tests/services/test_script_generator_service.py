"""
Tests for ScriptGeneratorService
"""
import pytest
import json
import os
from unittest.mock import Mock, patch, mock_open
from app.services.script_generator_service import ScriptGeneratorService


class TestScriptGeneratorService:
    """Test suite for ScriptGeneratorService."""

    @pytest.fixture
    def service(self, mock_anthropic_client, mock_settings):
        """Create service instance with mocked Claude client."""
        # Mock knowledge base loading
        with patch('app.services.script_generator_service.Anthropic', return_value=mock_anthropic_client), \
             patch('app.services.script_generator_service.settings', mock_settings), \
             patch('os.path.exists', return_value=False):  # No KB file for tests
            return ScriptGeneratorService()

    def test_load_knowledge_base_file_exists(self, mock_settings):
        """Test loading knowledge base when file exists."""
        # Arrange
        kb_data = {
            'Video Title 1': 'Transcript 1...',
            'Video Title 2': 'Transcript 2...'
        }

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()), \
             patch('pickle.load', return_value=kb_data), \
             patch('app.services.script_generator_service.Anthropic'), \
             patch('app.services.script_generator_service.settings', mock_settings):
            # Act
            service = ScriptGeneratorService()

            # Assert
            assert len(service.knowledge_base) == 2

    def test_load_knowledge_base_file_not_found(self, mock_settings):
        """Test loading knowledge base when file doesn't exist."""
        # Arrange
        with patch('os.path.exists', return_value=False), \
             patch('app.services.script_generator_service.Anthropic'), \
             patch('app.services.script_generator_service.settings', mock_settings):
            # Act
            service = ScriptGeneratorService()

            # Assert
            assert service.knowledge_base == {}

    def test_generate_script_success(self, service, mock_anthropic_client, mock_video_data, mock_angle, mock_research_brief, mock_creator_profile):
        """Test successful script generation."""
        # Arrange
        script_data = {
            'script': '[HOOK]\nTest hook\n[INTRO]\nTest intro\n[BODY]\nTest body\n[CONCLUSION]\nTest conclusion',
            'titles': ['Title 1', 'Title 2', 'Title 3', 'Title 4'],
            'thumbnails': ['Thumb 1', 'Thumb 2', 'Thumb 3', 'Thumb 4']
        }

        mock_content = Mock()
        mock_content.text = json.dumps(script_data)
        mock_message = Mock()
        mock_message.content = [mock_content]
        mock_anthropic_client.messages.create.return_value = mock_message

        # Act
        result = service.generate_script(
            video_data=mock_video_data,
            selected_angle=mock_angle,
            research_brief=mock_research_brief,
            profile=mock_creator_profile
        )

        # Assert
        assert result is not None
        assert 'script' in result
        assert 'titles' in result
        assert 'thumbnails' in result
        assert len(result['titles']) == 4
        assert len(result['thumbnails']) == 4
        mock_anthropic_client.messages.create.assert_called_once()

    def test_generate_script_with_knowledge_base(self, mock_anthropic_client, mock_settings):
        """Test script generation includes knowledge base."""
        # Arrange
        kb_data = {'Test Video': 'Test transcript...'}

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()), \
             patch('pickle.load', return_value=kb_data), \
             patch('app.services.script_generator_service.Anthropic', return_value=mock_anthropic_client), \
             patch('app.services.script_generator_service.settings', mock_settings):

            service = ScriptGeneratorService()

            script_data = {
                'script': 'Test script',
                'titles': ['T1', 'T2', 'T3', 'T4'],
                'thumbnails': ['TH1', 'TH2', 'TH3', 'TH4']
            }

            mock_content = Mock()
            mock_content.text = json.dumps(script_data)
            mock_message = Mock()
            mock_message.content = [mock_content]
            mock_anthropic_client.messages.create.return_value = mock_message

            # Act
            result = service.generate_script(
                video_data={'title': 'Test', 'transcript': 'Test', 'view_count': 1000},
                selected_angle={'angle_name': 'Test', 'core_hook': 'Test', 'key_differentiator': 'Test', 'target_emotion': 'curiosity'},
                research_brief={'executive_summary': 'Test', 'new_facts': [], 'narrative_hooks': []},
                profile={'creator_name': 'Test', 'niche': 'Test', 'expertise_areas': []}
            )

            # Assert
            assert result is not None

    def test_generate_script_with_markdown_response(self, service, mock_anthropic_client, mock_video_data, mock_angle, mock_research_brief, mock_creator_profile):
        """Test script generation with markdown code blocks."""
        # Arrange
        script_data = {
            'script': 'Test script',
            'titles': ['T1', 'T2', 'T3', 'T4'],
            'thumbnails': ['TH1', 'TH2', 'TH3', 'TH4']
        }

        markdown_response = f"```json\n{json.dumps(script_data)}\n```"
        mock_content = Mock()
        mock_content.text = markdown_response
        mock_message = Mock()
        mock_message.content = [mock_content]
        mock_anthropic_client.messages.create.return_value = mock_message

        # Act
        result = service.generate_script(
            video_data=mock_video_data,
            selected_angle=mock_angle,
            research_brief=mock_research_brief,
            profile=mock_creator_profile
        )

        # Assert
        assert result is not None
        assert 'script' in result

    def test_generate_script_fallback_on_error(self, service, mock_anthropic_client, mock_video_data, mock_angle, mock_research_brief, mock_creator_profile):
        """Test script generation fallback on error."""
        # Arrange
        mock_anthropic_client.messages.create.side_effect = Exception('API Error')

        # Act
        result = service.generate_script(
            video_data=mock_video_data,
            selected_angle=mock_angle,
            research_brief=mock_research_brief,
            profile=mock_creator_profile
        )

        # Assert
        assert result is not None
        assert 'script' in result
        assert 'titles' in result
        assert 'thumbnails' in result
        assert len(result['titles']) == 4

    def test_parse_script_response_valid(self, service):
        """Test parsing valid script response."""
        # Arrange
        script_data = {
            'script': 'Test script',
            'titles': ['T1', 'T2', 'T3', 'T4'],
            'thumbnails': ['TH1', 'TH2', 'TH3', 'TH4']
        }
        response_text = json.dumps(script_data)

        # Act
        result = service._parse_script_response(response_text)

        # Assert
        assert result is not None
        assert result['script'] == 'Test script'

    def test_parse_script_response_invalid(self, service):
        """Test parsing invalid script response."""
        # Arrange
        response_text = "Not valid JSON"

        # Act
        result = service._parse_script_response(response_text)

        # Assert
        assert result == {}

    def test_get_fallback_script(self, service, mock_video_data, mock_angle):
        """Test fallback script generation."""
        # Act
        result = service._get_fallback_script(mock_video_data, mock_angle)

        # Assert
        assert 'script' in result
        assert 'titles' in result
        assert 'thumbnails' in result
        assert len(result['titles']) == 4
        assert len(result['thumbnails']) == 4
        assert '[HOOK]' in result['script']
        assert '[INTRO]' in result['script']
        assert '[BODY]' in result['script']
        assert '[CONCLUSION]' in result['script']

    def test_format_script_for_display(self, service):
        """Test formatting script for display."""
        # Arrange
        script = "[HOOK]\nTest hook\n[INTRO]\nTest intro\n[BODY]\nTest body\n[CONCLUSION]\nTest conclusion"

        # Act
        result = service.format_script_for_display(script)

        # Assert
        assert '📌 HOOK' in result
        assert '🎬 INTRODUCTION' in result
        assert '📝 MAIN CONTENT' in result
        assert '🎯 CONCLUSION' in result
        assert '━━━━━━━━' in result  # Visual separators
