"""
Pytest configuration and shared fixtures for Viral Researcher tests.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import json


# ============================================================================
# Mock Data Fixtures
# ============================================================================

@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        'id': 'test-user-123',
        'email': 'test@example.com',
        'full_name': 'Test User'
    }


@pytest.fixture
def mock_creator_profile():
    """Mock creator profile."""
    return {
        'id': 1,
        'user_id': 'test-user-123',
        'creator_name': 'Tech Educator',
        'bio': 'I teach programming and tech topics',
        'niche': 'Technology Education',
        'expertise_areas': ['Python', 'JavaScript', 'AI'],
        'tone_preference': 'Educational',
        'target_audience': 'Beginner to intermediate developers',
        'additional_notes': 'Focus on practical examples',
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }


@pytest.fixture
def mock_video_data():
    """Mock viral video data."""
    return {
        'id': 1,
        'video_id': 'dQw4w9WgXcQ',
        'channel_id': 'UC123456789',
        'channel_name': 'Tech Channel',
        'title': 'How to Build a Viral App',
        'thumbnail_url': 'https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg',
        'view_count': 150000,
        'duration_seconds': 720,
        'published_at': '2024-01-15T10:00:00Z',
        'video_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'transcript': 'This is a sample transcript of the viral video...',
        'transcript_fetched_at': datetime.now().isoformat(),
        'view_bucket': '100k-1M',
        'scraped_at': datetime.now().isoformat(),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }


@pytest.fixture
def mock_angle():
    """Mock generated angle."""
    return {
        'angle_name': 'Technical Deep Dive',
        'core_hook': 'Everyone talks about the results, but nobody shows the code',
        'key_differentiator': 'Focus on actual implementation details',
        'target_emotion': 'curiosity',
        'estimated_appeal': 'high'
    }


@pytest.fixture
def mock_research_data():
    """Mock raw research data."""
    return {
        'video_topic': 'Building viral apps',
        'niche': 'Technology',
        'trending_topics': [
            {
                'title': 'Top 10 App Development Trends',
                'url': 'https://example.com/trends',
                'content': 'Recent trends in app development...',
                'score': 0.95
            }
        ],
        'fact_checks': [
            {
                'query': 'App development statistics',
                'verification': 'According to recent data, mobile apps...',
                'source': 'Perplexity AI'
            }
        ],
        'new_data': [],
        'scraped_content': [
            {
                'success': True,
                'url': 'https://example.com/article',
                'content': 'Article content here...',
                'metadata': {}
            }
        ]
    }


@pytest.fixture
def mock_research_brief():
    """Mock synthesized research brief from Gemini."""
    return {
        'executive_summary': 'Key findings about viral app development',
        'new_facts': [
            {
                'fact': '70% of viral apps use push notifications',
                'source': 'https://example.com/stats',
                'credibility': 'high',
                'placement_suggestion': 'body'
            }
        ],
        'updated_claims': [],
        'key_statistics': [
            {
                'statistic': '2.5M downloads',
                'context': 'Average for successful apps',
                'source': 'App Store data'
            }
        ],
        'compelling_quotes': [],
        'narrative_hooks': [
            'What if I told you most viral apps share one secret?',
            'The truth about app virality will surprise you',
            'Developers hate this one simple trick'
        ],
        'supporting_evidence': []
    }


@pytest.fixture
def mock_script_output():
    """Mock generated script output."""
    return {
        'script': '[HOOK]\nWhat if I told you...\n[INTRO]\nToday we\'re diving into...\n[BODY]\nHere are the facts...\n[CONCLUSION]\nSo there you have it...',
        'titles': [
            'The Secret to Building Viral Apps',
            'How I Got 1M Downloads in 30 Days',
            'App Development: What They Don\'t Tell You',
            'Building Apps That Go Viral (Step-by-Step)'
        ],
        'thumbnails': [
            'Split screen: before/after app success',
            'Creator pointing at 1M downloads stat',
            'Shocked face with app icon explosion',
            'Code on screen with surprised expression'
        ]
    }


@pytest.fixture
def mock_transcript_response():
    """Mock Apify transcript response."""
    return {
        'transcript': [
            {'text': 'This is the first part of the transcript. '},
            {'text': 'Here is the second part. '},
            {'text': 'And the final part of the video.'}
        ]
    }


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    mock = Mock()

    # Mock table operations
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.upsert.return_value = mock

    # Mock execute
    mock.execute.return_value = Mock(data=[])

    return mock


@pytest.fixture
def mock_youtube_service():
    """Mock YouTube service."""
    mock = Mock()
    mock.get_channel_info.return_value = {
        'channel_id': 'UC123456789',
        'title': 'Test Channel',
        'thumbnail': 'https://example.com/thumb.jpg',
        'uploads_playlist': 'UU123456789'
    }
    mock.get_recent_videos.return_value = []
    return mock


@pytest.fixture
def mock_apify_client():
    """Mock Apify client."""
    mock = Mock()
    mock.actor.return_value = mock
    mock.call.return_value = {'defaultDatasetId': 'dataset123'}
    mock.dataset.return_value = mock
    mock.iterate_items.return_value = []
    return mock


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic (Claude) client."""
    mock = Mock()

    # Mock message response
    mock_message = Mock()
    mock_content = Mock()
    mock_content.text = json.dumps({
        'angle_name': 'Test Angle',
        'core_hook': 'Test hook',
        'key_differentiator': 'Test diff',
        'target_emotion': 'curiosity',
        'estimated_appeal': 'high'
    })
    mock_message.content = [mock_content]

    mock.messages.create.return_value = mock_message

    return mock


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client."""
    mock = Mock()

    # Mock generate_content response
    mock_response = Mock()
    mock_response.text = json.dumps({
        'executive_summary': 'Test summary',
        'new_facts': [],
        'narrative_hooks': []
    })

    mock.models.generate_content.return_value = mock_response

    return mock


@pytest.fixture
def mock_exa_client():
    """Mock Exa AI client."""
    mock = Mock()

    # Mock search response
    mock_result = Mock()
    mock_result.title = 'Test Article'
    mock_result.url = 'https://example.com/test'
    mock_result.text = 'Test content'
    mock_result.score = 0.9

    mock_response = Mock()
    mock_response.results = [mock_result]

    mock.search_and_contents.return_value = mock_response

    return mock


@pytest.fixture
def mock_perplexity_client():
    """Mock Perplexity (OpenAI-compatible) client."""
    mock = Mock()

    # Mock chat completion response
    mock_message = Mock()
    mock_message.content = 'Test perplexity response with facts and sources'

    mock_choice = Mock()
    mock_choice.message = mock_message

    mock_response = Mock()
    mock_response.choices = [mock_choice]

    mock.chat.completions.create.return_value = mock_response

    return mock


@pytest.fixture
def mock_firecrawl_client():
    """Mock Firecrawl client."""
    mock = Mock()
    mock.scrape_url.return_value = {
        'markdown': 'Test scraped content',
        'html': '<p>Test scraped content</p>',
        'metadata': {'title': 'Test Page'}
    }
    return mock


# ============================================================================
# Settings Fixture
# ============================================================================

@pytest.fixture
def mock_settings():
    """Mock application settings."""
    mock = Mock()
    mock.apify_api_key = 'test-apify-key'
    mock.apify_transcript_actor = 'test-actor-id'
    mock.exa_api_key = 'test-exa-key'
    mock.perplexity_api_key = 'test-perplexity-key'
    mock.firecrawl_api_key = 'test-firecrawl-key'
    mock.anthropic_api_key = 'test-anthropic-key'
    mock.gemini_api_key = 'test-gemini-key'
    mock.google_api_key = 'test-google-key'
    mock.gemini_model = 'gemini-2.0-flash'
    mock.claude_model = 'claude-3-5-sonnet-20241022'
    mock.video_min_duration = 300
    mock.max_videos_per_channel = 100
    mock.transcript_timeout = 60
    mock.data_dir = 'data'
    return mock
