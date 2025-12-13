import re
import os
import uuid
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def parse_iso_duration(duration_iso: str) -> int:
    """
    Parse ISO 8601 duration (e.g., PT1H5M30S) into total seconds.

    Args:
        duration_iso: ISO 8601 duration string

    Returns:
        Total duration in seconds
    """
    if not duration_iso:
        return 0

    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds


def format_duration(seconds: int) -> str:
    """
    Format seconds into MM:SS or HH:MM:SS format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 3600:
        minutes, secs = divmod(seconds, 60)
        return f"{minutes}:{secs:02d}"
    else:
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours}:{minutes:02d}:{secs:02d}"


def format_view_count(views: Optional[int]) -> str:
    """
    Format view count in YouTube style (e.g., 1.2M, 450K).

    Args:
        views: Number of views

    Returns:
        Formatted view count string
    """
    if views is None:
        return "0 views"

    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M views"
    elif views >= 1_000:
        return f"{views / 1_000:.0f}K views"
    else:
        return f"{views} views"


def format_time_ago(published_at: str) -> str:
    """
    Format published date as "X days/months/years ago".

    Args:
        published_at: ISO 8601 datetime string

    Returns:
        Human-readable time ago string
    """
    try:
        pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        now = datetime.now(pub_date.tzinfo)
        delta = now - pub_date

        if delta.days >= 365:
            years = delta.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif delta.days >= 30:
            months = delta.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    except Exception as e:
        logger.error(f"Error formatting time ago: {e}")
        return "Recently"


def save_uploaded_file(file_data: bytes, filename: str, upload_dir: str) -> str:
    """
    Save uploaded file with unique name.

    Args:
        file_data: File bytes
        filename: Original filename
        upload_dir: Directory to save file

    Returns:
        Path to saved file
    """
    # Create upload directory if it doesn't exist
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename
    ext = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    # Save file
    with open(file_path, 'wb') as f:
        f.write(file_data)

    return file_path


def is_shorts(duration_seconds: Optional[int], threshold: int = 60) -> bool:
    """
    Determine if a video is a YouTube Short based on duration.

    Args:
        duration_seconds: Video duration in seconds
        threshold: Duration threshold (default: 60 seconds)

    Returns:
        True if video is a Short
    """
    return duration_seconds is not None and duration_seconds < threshold
