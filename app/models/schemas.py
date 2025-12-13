from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime


class VideoData(BaseModel):
    """YouTube video data model."""
    video_id: str
    title: str
    channel_name: str
    channel_id: str
    thumbnail_url: str
    view_count: Optional[int] = None
    published_at: str
    duration_seconds: Optional[int] = None
    video_url: str


class UserVideo(BaseModel):
    """User-uploaded video for injection."""
    title: str
    thumbnail_path: str
    channel_name: str = "Your Channel"
    channel_avatar_path: Optional[str] = None
    duration: str = "10:00"  # Placeholder duration


class ChannelInfo(BaseModel):
    """YouTube channel information."""
    channel_id: str
    channel_name: str
    handle: str


class PersonaRequest(BaseModel):
    """Request payload for persona-based thumbnail testing."""
    persona: str = Field(..., min_length=10, max_length=1000)
    video_title: str = Field(..., min_length=1, max_length=100)


class GenerateResponse(BaseModel):
    """Response from generate endpoint."""
    success: bool
    message: str
    video_count: int = 0
    html: Optional[str] = None


class ShuffleRequest(BaseModel):
    """Request to shuffle existing results."""
    session_id: str


class CSVLogEntry(BaseModel):
    """Entry for competitor_data.csv logging."""
    timestamp: datetime
    persona: str
    channel_handle: str
    channel_id: str
    video_id: str
    title: str
    views: Optional[int]
    published_at: str
    thumbnail_url: str
    duration_seconds: Optional[int] = None

    def to_dict(self):
        """Convert to dict for CSV writing."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'persona': self.persona,
            'channel_handle': self.channel_handle,
            'channel_id': self.channel_id,
            'video_id': self.video_id,
            'title': self.title,
            'views': self.views,
            'published_at': self.published_at,
            'thumbnail_url': self.thumbnail_url,
            'duration_seconds': self.duration_seconds
        }
