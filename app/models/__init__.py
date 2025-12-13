"""
Models for YouTube Context Engine.
Includes database models and API schemas.
"""

# Database models
from app.models.database import (
    Profile,
    UserAPIKey,
    YouTubeChannel,
    YouTubeVideo,
    ThumbnailTest,
    TestVideo,
    UsageLog,
    SubscriptionTier,
    TestStatus,
    ProfileCreate,
    ProfileUpdate,
    UserAPIKeyCreate,
    ThumbnailTestCreate,
    UsageLogCreate
)

# API schemas
from app.models.schemas import (
    VideoData,
    UserVideo,
    ChannelInfo,
    PersonaRequest,
    GenerateResponse,
    ShuffleRequest,
    CSVLogEntry
)

__all__ = [
    # Database models
    'Profile',
    'UserAPIKey',
    'YouTubeChannel',
    'YouTubeVideo',
    'ThumbnailTest',
    'TestVideo',
    'UsageLog',
    'SubscriptionTier',
    'TestStatus',
    'ProfileCreate',
    'ProfileUpdate',
    'UserAPIKeyCreate',
    'ThumbnailTestCreate',
    'UsageLogCreate',
    # API schemas
    'VideoData',
    'UserVideo',
    'ChannelInfo',
    'PersonaRequest',
    'GenerateResponse',
    'ShuffleRequest',
    'CSVLogEntry'
]
