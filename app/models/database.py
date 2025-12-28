"""
Database models matching Supabase schema.
These models represent the structure of data stored in the database.
"""

from pydantic import BaseModel, Field, UUID4
from typing import Optional, List
from datetime import datetime, timedelta
from enum import Enum


class SubscriptionTier(str, Enum):
    """User subscription tiers."""
    FREE = "free"
    PRO = "pro"


class TestStatus(str, Enum):
    """Thumbnail test processing status."""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================
# 1. PROFILES - User Profile Extension
# ============================================

class Profile(BaseModel):
    """User profile extending Supabase auth.users."""
    id: UUID4
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

    # Subscription
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    tests_used_this_month: int = 0
    tests_limit: int = 5

    # Stripe billing
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    billing_cycle_start: datetime = Field(default_factory=datetime.now)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


# ============================================
# 2. USER API KEYS - User's Own Google API Keys
# ============================================

class UserAPIKey(BaseModel):
    """User's own Google API key for unlimited tests."""
    id: UUID4
    user_id: UUID4

    # Encrypted API key (one key for YouTube + Gemini)
    google_api_key_encrypted: Optional[str] = None

    # Validation
    key_verified: bool = False
    last_verified_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============================================
# 3. YOUTUBE CHANNELS - Cached Channel Data
# ============================================

class YouTubeChannel(BaseModel):
    """Cached YouTube channel data (shared across all users)."""
    id: UUID4

    # Channel identifiers
    channel_id: str  # UC...
    channel_handle: str  # @MrBeast
    channel_name: Optional[str] = None  # MrBeast
    channel_avatar_url: Optional[str] = None

    # Stats
    subscriber_count: Optional[int] = None

    # Cache metadata
    last_fetched_at: datetime = Field(default_factory=datetime.now)
    fetch_count: int = 1
    created_at: datetime = Field(default_factory=datetime.now)


# ============================================
# 4. YOUTUBE VIDEOS - Cached Video Data
# ============================================

class YouTubeVideo(BaseModel):
    """Cached YouTube video data (shared across all users)."""
    id: UUID4

    # Video identifiers
    video_id: str
    channel_id: str

    # Video metadata
    title: str
    thumbnail_url: str  # YouTube CDN URL (never expires)
    view_count: Optional[int] = None
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    is_short: bool = False

    # Cache metadata (no expiry - keep forever)
    last_fetched_at: datetime = Field(default_factory=datetime.now)
    fetch_count: int = 1
    created_at: datetime = Field(default_factory=datetime.now)


# ============================================
# 5. THUMBNAIL TESTS - User's Test Runs
# ============================================

class ThumbnailTest(BaseModel):
    """User's thumbnail test run."""
    id: UUID4
    user_id: UUID4

    # Input data
    persona: str
    video_title: str

    # File paths (local storage - files deleted after 24h)
    thumbnail_path: str  # "static/uploads/abc.png"
    avatar_path: Optional[str] = None
    thumbnail_expires_at: datetime = Field(
        default_factory=lambda: datetime.now() + timedelta(hours=24)
    )

    # Results summary
    status: TestStatus = TestStatus.PROCESSING
    channels_discovered: Optional[List[str]] = None  # ["@MrBeast", "@Veritasium"]
    total_videos_fetched: Optional[int] = None

    # API usage tracking
    used_user_api_key: bool = False

    # Timestamps (keep records forever - only delete thumbnail files)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


# ============================================
# 6. TEST VIDEOS - Videos in Each Test
# ============================================

class TestVideo(BaseModel):
    """Link between thumbnail tests and YouTube videos."""
    id: UUID4
    test_id: UUID4
    video_id: UUID4

    # Position in this specific test (0-indexed)
    position: int
    is_user_video: bool = False

    created_at: datetime = Field(default_factory=datetime.now)


# ============================================
# 7. USAGE LOGS - Analytics & Audit Trail
# ============================================

class UsageLog(BaseModel):
    """Analytics and audit trail for user actions."""
    id: UUID4
    user_id: UUID4

    # Action tracking
    action: str  # 'test_created', 'api_key_added', 'subscription_upgraded'
    metadata: Optional[dict] = None  # Flexible additional data

    created_at: datetime = Field(default_factory=datetime.now)


# ============================================
# CREATE/UPDATE SCHEMAS (for API requests)
# ============================================

class ProfileCreate(BaseModel):
    """Schema for creating a new profile."""
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class ProfileUpdate(BaseModel):
    """Schema for updating a profile."""
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserAPIKeyCreate(BaseModel):
    """Schema for adding a new API key."""
    google_api_key: str  # Plain text - will be encrypted before storage


class ThumbnailTestCreate(BaseModel):
    """Schema for creating a new thumbnail test."""
    persona: str
    video_title: str
    thumbnail_path: str
    avatar_path: Optional[str] = None


class UsageLogCreate(BaseModel):
    """Schema for creating a usage log entry."""
    action: str
    metadata: Optional[dict] = None


# ============================================
# 8. PRODUCTION PROJECTS - Video Production Planning
# ============================================

class ProductionProject(BaseModel):
    """Project for organizing production videos (e.g., 'Tech Channel', 'Vlog Series')."""
    id: UUID4
    user_id: UUID4
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ProductionProjectCreate(BaseModel):
    """Schema for creating a new production project."""
    name: str
    description: Optional[str] = None


class ProductionProjectUpdate(BaseModel):
    """Schema for updating a production project."""
    name: Optional[str] = None
    description: Optional[str] = None


# ============================================
# 9. PRODUCTION VIDEOS - Video Metadata & Planning
# ============================================

class FontPreference(str, Enum):
    """Font preference for script display."""
    MONO = "mono"
    SERIF = "serif"


class ProductionVideo(BaseModel):
    """Video production metadata and planning details."""
    id: UUID4
    user_id: UUID4
    title: str
    project_id: Optional[UUID4] = None

    # Planning fields
    idea: Optional[str] = None
    hook: Optional[str] = None
    thumbnail_description: Optional[str] = None
    notes: Optional[str] = None
    global_vibe: Optional[str] = None

    # Display preferences
    font_preference: FontPreference = FontPreference.MONO
    custom_column_defs: Optional[List[dict]] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class ProductionVideoCreate(BaseModel):
    """Schema for creating a new production video."""
    title: str
    project_id: Optional[UUID4] = None
    idea: Optional[str] = None


class ProductionVideoUpdate(BaseModel):
    """Schema for updating a production video."""
    title: Optional[str] = None
    project_id: Optional[UUID4] = None
    idea: Optional[str] = None
    hook: Optional[str] = None
    thumbnail_description: Optional[str] = None
    notes: Optional[str] = None
    global_vibe: Optional[str] = None
    font_preference: Optional[FontPreference] = None


# ============================================
# 10. PRODUCTION SHOTS - Individual Shots in Videos
# ============================================

class ProductionShot(BaseModel):
    """Individual shot within a video production with creative and technical specs."""
    id: UUID4
    video_id: UUID4
    order_index: int = 0

    # Shot details
    shot_description: Optional[str] = None
    shot_type: Optional[str] = None
    script_line: Optional[str] = None

    # Creative details
    music_link: Optional[str] = None
    vibes: Optional[List[str]] = Field(default_factory=list)
    music_vibes: Optional[List[str]] = Field(default_factory=list)
    music_inspiration: Optional[str] = None
    roll_type: Optional[str] = None

    # Flexible extra data
    extra_data: Optional[dict] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ProductionShotCreate(BaseModel):
    """Schema for creating a new production shot."""
    video_id: UUID4
    order_index: int = 0
    shot_description: Optional[str] = None
    shot_type: Optional[str] = None


class ProductionShotUpdate(BaseModel):
    """Schema for updating a production shot."""
    order_index: Optional[int] = None
    shot_description: Optional[str] = None
    shot_type: Optional[str] = None
    script_line: Optional[str] = None
    music_link: Optional[str] = None
    vibes: Optional[List[str]] = None
    music_vibes: Optional[List[str]] = None
    music_inspiration: Optional[str] = None
    roll_type: Optional[str] = None
    extra_data: Optional[dict] = None


# ============================================
# 11. HOOK LIBRARY - Saved Hooks for Reuse
# ============================================

class HookCategory(str, Enum):
    """Categories for organizing hooks."""
    CURIOSITY = "curiosity"
    CONTROVERSY = "controversy"
    STORY = "story"
    QUESTION = "question"
    STATISTIC = "statistic"
    CHALLENGE = "challenge"
    PROMISE = "promise"
    SHOCK = "shock"
    OTHER = "other"


class Hook(BaseModel):
    """Saved hook for reuse across scripts."""
    id: UUID4
    user_id: UUID4

    # Hook content
    hook_text: str
    category: HookCategory = HookCategory.OTHER

    # Source tracking
    source_script_id: Optional[int] = None  # Which script it came from
    source_video_title: Optional[str] = None  # Original video title
    source_angle: Optional[str] = None  # Angle that generated it

    # Organization
    tags: List[str] = Field(default_factory=list)
    is_favorite: bool = False
    use_count: int = 0  # Track how many times used

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class HookCreate(BaseModel):
    """Schema for creating a new hook."""
    hook_text: str
    category: Optional[HookCategory] = HookCategory.OTHER
    source_script_id: Optional[int] = None
    source_video_title: Optional[str] = None
    source_angle: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)


class HookUpdate(BaseModel):
    """Schema for updating a hook."""
    hook_text: Optional[str] = None
    category: Optional[HookCategory] = None
    tags: Optional[List[str]] = None
    is_favorite: Optional[bool] = None
