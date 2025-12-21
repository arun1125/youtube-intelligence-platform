"""
Tests for ResearchService and ResearchSynthesisService
"""
import pytest
import json
from unittest.mock import Mock, patch
from app.services.research_service import ResearchService
from app.services.research_synthesis_service import ResearchSynthesisService


class TestResearchService:
    """Test suite for ResearchService."""

    @pytest.fixture
    def service(self, mock_exa_client, mock_perplexity_client, mock_firecrawl_client, mock_settings):
        """Create service instance with mocked API clients."""
        with patch('app.services.research_service.Exa', return_value=mock_exa_client), \
             patch('app.services.research_service.OpenAI', return_value=mock_perplexity_client), \
             patch('app.services.research_service.FirecrawlApp', return_value=mock_firecrawl_client), \
             patch('app.services.research_service.settings', mock_settings):
            return ResearchService()

    def test_exa_search_success(self, service, mock_exa_client):
        """Test successful Exa search."""
        # Act
        result = service._exa_search('test query', num_results=5)

        # Assert
        assert result['success'] is True
        assert len(result['results']) == 1
        assert result['results'][0]['title'] == 'Test Article'
        mock_exa_client.search_and_contents.assert_called_once()

    def test_exa_search_failure(self, service, mock_exa_client):
        """Test Exa search failure."""
        # Arrange
        mock_exa_client.search_and_contents.side_effect = Exception('API Error')

        # Act
        result = service._exa_search('test query')

        # Assert
        assert result['success'] is False
        assert 'error' in result

    def test_perplexity_search_success(self, service, mock_perplexity_client):
        """Test successful Perplexity search."""
        # Act
        result = service._perplexity_search('test fact check query')

        # Assert
        assert result['success'] is True
        assert 'Test perplexity response' in result['content']
        mock_perplexity_client.chat.completions.create.assert_called_once()

    def test_perplexity_search_failure(self, service, mock_perplexity_client):
        """Test Perplexity search failure."""
        # Arrange
        mock_perplexity_client.chat.completions.create.side_effect = Exception('API Error')

        # Act
        result = service._perplexity_search('test query')

        # Assert
        assert result['success'] is False
        assert 'error' in result

    def test_firecrawl_scrape_success(self, service, mock_firecrawl_client):
        """Test successful Firecrawl scraping."""
        # Act
        result = service._firecrawl_scrape('https://example.com')

        # Assert
        assert result['success'] is True
        assert 'Test scraped content' in result['content']
        mock_firecrawl_client.scrape_url.assert_called_once()

    def test_firecrawl_scrape_failure(self, service, mock_firecrawl_client):
        """Test Firecrawl scraping failure."""
        # Arrange
        mock_firecrawl_client.scrape_url.side_effect = Exception('Scrape Error')

        # Act
        result = service._firecrawl_scrape('https://example.com')

        # Assert
        assert result['success'] is False
        assert 'error' in result

    def test_gather_research_full_workflow(self, service, mock_exa_client, mock_perplexity_client, mock_firecrawl_client):
        """Test complete research gathering workflow."""
        # Act
        result = service.gather_research(
            video_topic='Building viral apps',
            niche='Technology',
            transcript_summary='Test summary',
            claims=['Apps need push notifications']
        )

        # Assert
        assert 'trending_topics' in result
        assert 'fact_checks' in result
        assert 'scraped_content' in result
        assert len(result['trending_topics']) > 0
        assert len(result['fact_checks']) > 0

    def test_extract_claims_from_transcript(self, service):
        """Test extracting claims from transcript."""
        # Arrange
        transcript = """
        The app has 1 million downloads.
        Push notifications are essential.
        This is a short sentence.
        Our platform will revolutionize the industry.
        Research shows that 70% of users prefer dark mode.
        """

        # Act
        claims = service.extract_claims_from_transcript(transcript, max_claims=3)

        # Assert
        assert len(claims) <= 3
        assert isinstance(claims, list)


class TestResearchSynthesisService:
    """Test suite for ResearchSynthesisService."""

    @pytest.fixture
    def service(self, mock_gemini_client, mock_settings):
        """Create service instance with mocked Gemini client."""
        with patch('app.services.research_synthesis_service.genai.Client', return_value=mock_gemini_client), \
             patch('app.services.research_synthesis_service.settings', mock_settings):
            return ResearchSynthesisService()

    def test_synthesize_research_success(self, service, mock_gemini_client, mock_video_data, mock_angle, mock_research_data, mock_creator_profile):
        """Test successful research synthesis."""
        # Arrange
        brief_data = {
            'executive_summary': 'Test summary',
            'new_facts': [
                {
                    'fact': 'Test fact',
                    'source': 'example.com',
                    'credibility': 'high',
                    'placement_suggestion': 'body'
                }
            ],
            'updated_claims': [],
            'key_statistics': [],
            'compelling_quotes': [],
            'narrative_hooks': ['Hook 1', 'Hook 2', 'Hook 3'],
            'supporting_evidence': []
        }

        mock_response = Mock()
        mock_response.text = json.dumps(brief_data)
        mock_gemini_client.models.generate_content.return_value = mock_response

        # Act
        result = service.synthesize_research(
            video_data=mock_video_data,
            selected_angle=mock_angle,
            raw_research=mock_research_data,
            profile=mock_creator_profile
        )

        # Assert
        assert result is not None
        assert 'executive_summary' in result
        assert 'new_facts' in result
        assert 'narrative_hooks' in result
        assert len(result['narrative_hooks']) == 3
        mock_gemini_client.models.generate_content.assert_called_once()

    def test_synthesize_research_with_markdown(self, service, mock_gemini_client, mock_video_data, mock_angle, mock_research_data, mock_creator_profile):
        """Test research synthesis with markdown code blocks."""
        # Arrange
        brief_data = {
            'executive_summary': 'Test',
            'new_facts': [],
            'narrative_hooks': []
        }

        markdown_response = f"```json\n{json.dumps(brief_data)}\n```"
        mock_response = Mock()
        mock_response.text = markdown_response
        mock_gemini_client.models.generate_content.return_value = mock_response

        # Act
        result = service.synthesize_research(
            video_data=mock_video_data,
            selected_angle=mock_angle,
            raw_research=mock_research_data,
            profile=mock_creator_profile
        )

        # Assert
        assert result is not None
        assert 'executive_summary' in result

    def test_synthesize_research_fallback(self, service, mock_gemini_client, mock_video_data, mock_angle, mock_research_data, mock_creator_profile):
        """Test research synthesis fallback on error."""
        # Arrange
        mock_gemini_client.models.generate_content.side_effect = Exception('API Error')

        # Act
        result = service.synthesize_research(
            video_data=mock_video_data,
            selected_angle=mock_angle,
            raw_research=mock_research_data,
            profile=mock_creator_profile
        )

        # Assert
        assert result is not None
        assert 'executive_summary' in result
        assert isinstance(result['new_facts'], list)

    def test_parse_synthesis_response_valid(self, service):
        """Test parsing valid synthesis response."""
        # Arrange
        brief_data = {
            'executive_summary': 'Test',
            'new_facts': [],
            'narrative_hooks': []
        }
        response_text = json.dumps(brief_data)

        # Act
        result = service._parse_synthesis_response(response_text)

        # Assert
        assert result is not None
        assert result['executive_summary'] == 'Test'

    def test_parse_synthesis_response_invalid(self, service):
        """Test parsing invalid synthesis response."""
        # Arrange
        response_text = "Not valid JSON"

        # Act
        result = service._parse_synthesis_response(response_text)

        # Assert
        assert result == {}

    def test_get_fallback_brief(self, service, mock_research_data):
        """Test fallback brief generation."""
        # Act
        result = service._get_fallback_brief(mock_research_data)

        # Assert
        assert 'executive_summary' in result
        assert 'new_facts' in result
        assert 'narrative_hooks' in result
        assert len(result['new_facts']) > 0
