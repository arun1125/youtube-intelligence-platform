import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from googleapiclient.discovery import build
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path to import channel_resolver
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.utils.channel_resolver import get_channel_id_from_html

# --- CONFIGURATION ---
YOUTUBE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Validate API keys
if not YOUTUBE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

# Setup Clients
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)


def resolve_channel_input(channel_input: str) -> Optional[str]:
    """
    Convert channel URL, @ handle, or channel name to channel ID.

    Args:
        channel_input: Can be:
            - Channel URL: https://www.youtube.com/@ThePrimeagen
            - @ handle: @ThePrimeagen
            - Channel name: ThePrimeagen
            - Channel ID: UC... (returned as-is)

    Returns:
        Channel ID (UC...) or None if not found
    """
    # If already a channel ID, return it
    if channel_input.startswith("UC") and len(channel_input) == 24:
        print(f"✓ Using provided channel ID: {channel_input}")
        return channel_input

    # Extract handle from URL if needed
    if "youtube.com" in channel_input:
        # Extract @handle from URL like https://www.youtube.com/@ThePrimeagen
        if "/@" in channel_input:
            channel_input = "@" + channel_input.split("/@")[1].split("/")[0].split("?")[0]
        # Extract from /c/ or /channel/ URLs
        elif "/c/" in channel_input:
            channel_input = channel_input.split("/c/")[1].split("/")[0].split("?")[0]
        elif "/channel/" in channel_input:
            # Already a channel ID in URL
            return channel_input.split("/channel/")[1].split("/")[0].split("?")[0]

    # Use the existing channel resolver
    print(f"Resolving channel: {channel_input}")
    channel_id, url = get_channel_id_from_html(channel_input)

    if channel_id:
        print(f"✓ Resolved to channel ID: {channel_id}")
        print(f"  URL: {url}")
        return channel_id
    else:
        print(f"✗ Failed to resolve channel: {channel_input}")
        return None


def parse_duration(duration_str: str) -> int:
    """
    Parse ISO 8601 duration format to seconds.

    Args:
        duration_str: Duration in ISO 8601 format (e.g., "PT15M33S")

    Returns:
        Duration in seconds
    """
    import re

    # Pattern to match ISO 8601 duration: PT1H2M3S
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)

    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds


def get_thumbnail_urls(channel_id: str, max_videos: int = 20, days_back: int = 365, min_duration_seconds: int = 180) -> List[Tuple[str, str, str]]:
    """
    Get thumbnail URLs from recent videos in a channel.

    Args:
        channel_id: YouTube channel ID (UC...)
        max_videos: Maximum number of videos to fetch (default: 20)
        days_back: Only include videos from the last N days (default: 365)
        min_duration_seconds: Minimum video duration in seconds (default: 180 = 3 minutes)

    Returns:
        List of tuples: (thumbnail_url, video_title, published_date)
    """
    from datetime import timezone

    # Calculate the cutoff date (timezone-aware)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    cutoff_date_str = cutoff_date.isoformat()

    print(f"\nFetching videos published after: {cutoff_date.strftime('%Y-%m-%d')}")
    print(f"Minimum duration: {min_duration_seconds // 60} minutes")

    # 1. Get the "Uploads" playlist ID for the channel
    try:
        ch_request = youtube.channels().list(part="contentDetails,snippet", id=channel_id)
        ch_response = ch_request.execute()

        if not ch_response.get('items'):
            print(f"✗ Channel not found: {channel_id}")
            return []

        channel_title = ch_response['items'][0]['snippet']['title']
        print(f"✓ Found channel: {channel_title}")

        uploads_playlist_id = ch_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    except Exception as e:
        print(f"✗ Error fetching channel details: {e}")
        return []

    # 2. Get videos from that playlist
    videos = []
    next_page_token = None
    total_fetched = 0
    filtered_out = 0

    while len(videos) < max_videos:
        try:
            pl_request = youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=50,  # Fetch more to account for filtering
                pageToken=next_page_token
            )
            pl_response = pl_request.execute()

            # Collect video IDs to fetch durations
            video_ids = []
            video_data = {}

            for item in pl_response['items']:
                # Check if video is within date range
                published_at = item['snippet']['publishedAt']
                published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))

                if published_date < cutoff_date:
                    # Videos are sorted by date, so we can stop here
                    print(f"  Reached videos older than {days_back} days")
                    break

                video_id = item['contentDetails']['videoId']
                video_ids.append(video_id)

                # Try to get the highest resolution available
                thumbs = item['snippet']['thumbnails']
                url = thumbs.get('maxres', thumbs.get('high', thumbs.get('default')))['url']
                title = item['snippet']['title']

                video_data[video_id] = {
                    'url': url,
                    'title': title,
                    'published_at': published_at
                }

                total_fetched += 1

            # Fetch video durations in batch
            if video_ids:
                video_request = youtube.videos().list(
                    part="contentDetails",
                    id=','.join(video_ids)
                )
                video_response = video_request.execute()

                for video_item in video_response['items']:
                    video_id = video_item['id']
                    duration_str = video_item['contentDetails']['duration']
                    duration_seconds = parse_duration(duration_str)

                    # Filter by duration
                    if duration_seconds >= min_duration_seconds:
                        data = video_data[video_id]
                        videos.append((data['url'], data['title'], data['published_at']))

                        if len(videos) >= max_videos:
                            break
                    else:
                        filtered_out += 1

            next_page_token = pl_response.get('nextPageToken')
            if not next_page_token or len(videos) >= max_videos:
                break

        except Exception as e:
            print(f"✗ Error fetching videos: {e}")
            break

    print(f"✓ Found {len(videos)} videos from the last {days_back} days (filtered out {filtered_out} short videos)")
    return videos


def analyze_style_with_gemini(thumbnail_data: List[Tuple[str, str, str]]) -> str:
    """
    Analyze thumbnail style using Gemini AI.

    Args:
        thumbnail_data: List of (url, title, date) tuples

    Returns:
        JSON string with style analysis
    """
    thumbnail_urls = [url for url, _, _ in thumbnail_data]

    prompt = f"""
Analyze the following {len(thumbnail_urls)} YouTube thumbnail URLs and describe the creator's 'Visual Brand Identity'.
Provide the output in STRICT JSON format with these keys:
- primary_color_palette (list of colors)
- typography_style (e.g., bold, serif, handwritten, modern sans-serif)
- face_presence (boolean: is the creator's face usually visible?)
- graphic_elements (e.g., arrows, emojis, borders, circles, text highlights)
- emotional_tone (e.g., energetic, professional, clickbait, minimal, educational)
- text_density (low, medium, high - how much text is on thumbnails)
- common_themes (list of recurring visual themes or patterns)
- thumbnail_layout (e.g., centered subject, split screen, text-focused, image-dominant)

URLs:
{chr(10).join(f"{i+1}. {url}" for i, url in enumerate(thumbnail_urls))}

Return ONLY valid JSON, no markdown code blocks or additional text.
"""

    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        return response.text
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return f'{{"error": "Gemini API quota exceeded. Please wait a few minutes and try again.", "details": "Rate limit hit - try again in ~60 seconds"}}'
        elif "404" in error_msg:
            return f'{{"error": "Gemini model not available. Try using gemini-1.5-pro or gemini-1.5-flash-8b instead.", "details": "{error_msg[:200]}"}}'
        else:
            return f'{{"error": "Failed to analyze thumbnails", "details": "{error_msg[:200]}"}}'


# --- MAIN EXECUTION ---
def main(channel_input: str, max_videos: int = 20, days_back: int = 365, skip_ai_analysis: bool = False, min_duration_minutes: int = 3):
    """
    Main function to analyze YouTube channel thumbnails.

    Args:
        channel_input: Channel URL, @ handle, or channel ID
        max_videos: Number of videos to analyze (default: 20)
        days_back: Only analyze videos from last N days (default: 365)
        skip_ai_analysis: Skip Gemini analysis (useful for testing video fetching)
        min_duration_minutes: Minimum video duration in minutes (default: 3)
    """
    print("=" * 60)
    print("YouTube Thumbnail Style Analyzer")
    print("=" * 60)

    # Step 1: Resolve channel to ID
    channel_id = resolve_channel_input(channel_input)
    if not channel_id:
        print("\n✗ Could not resolve channel. Please check the input and try again.")
        return

    # Step 2: Get thumbnails
    print(f"\nFetching up to {max_videos} thumbnails from the last {days_back} days...")
    thumbnail_data = get_thumbnail_urls(channel_id, max_videos=max_videos, days_back=days_back, min_duration_seconds=min_duration_minutes * 60)

    if not thumbnail_data:
        print("\n✗ No videos found in the specified date range.")
        return

    # Display fetched videos
    print(f"\n📹 Videos to analyze:")
    for i, (url, title, date) in enumerate(thumbnail_data[:5], 1):
        print(f"  {i}. {title[:60]}... ({date[:10]})")
    if len(thumbnail_data) > 5:
        print(f"  ... and {len(thumbnail_data) - 5} more")

    # Save thumbnail data to file for manual prompt engineering
    save_thumbnails_to_file(channel_id, thumbnail_data, channel_name=channel_input)

    if skip_ai_analysis:
        print("\n⏭️  Skipping AI analysis (test mode)")
        print("\n✅ Video fetching successful!")
        print(f"   Total videos: {len(thumbnail_data)}")
        print("\nThumbnail URLs:")
        for i, (url, title, _) in enumerate(thumbnail_data, 1):
            print(f"  {i}. {url}")
        return

    # Step 3: Analyze with Gemini
    print("\n🤖 Analyzing thumbnail style with Gemini AI...")
    style_profile = analyze_style_with_gemini(thumbnail_data)

    # Step 4: Display results
    print("\n" + "=" * 60)
    print("📊 THUMBNAIL STYLE PROFILE")
    print("=" * 60)
    print(style_profile)
    print("=" * 60)


def save_thumbnails_to_file(channel_id: str, thumbnail_data: List[Tuple[str, str, str]], channel_name: str = None, output_dir: str = "thumbnail_data"):
    """
    Save thumbnail URLs and metadata to a JSON file for manual prompt engineering.

    Args:
        channel_id: YouTube channel ID
        thumbnail_data: List of (url, title, date) tuples
        channel_name: Original channel input (handle, URL, or name)
        output_dir: Directory to save the file (default: "thumbnail_data")

    Returns:
        Path to the saved file
    """
    import json
    from pathlib import Path

    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{channel_id}_{timestamp}.json"
    filepath = output_path / filename

    # Prepare data structure
    data = {
        "channel_id": channel_id,
        "channel_name": channel_name or channel_id,
        "fetch_date": datetime.now().isoformat(),
        "total_videos": len(thumbnail_data),
        "videos": [
            {
                "index": i + 1,
                "title": title,
                "thumbnail_url": url,
                "published_date": date
            }
            for i, (url, title, date) in enumerate(thumbnail_data)
        ]
    }

    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Saved thumbnail data to: {filepath}")
    return str(filepath)


if __name__ == "__main__":
    # ========================================
    # CONFIGURATION: Add channels here
    # ========================================
    # You can use any of these formats:
    # - @ handle: "@ThePrimeagen"
    # - Channel URL: "https://www.youtube.com/@ThePrimeagen"
    # - Channel ID: "UC_x5XG1OV2P6uZZ5FSM9Ttw"

    CHANNELS_TO_ANALYZE = [
        "@MrBeast",
        # Add more channels here...
    ]

    # Settings for thumbnail extraction
    MAX_VIDEOS = 20          # Number of videos per channel
    DAYS_BACK = 365          # Only analyze videos from last N days
    MIN_DURATION_MIN = 3     # Minimum video duration in minutes
    SKIP_AI_ANALYSIS = True  # Set to False to enable Gemini analysis

    # ========================================
    # Process all channels
    # ========================================
    print("=" * 60)
    print(f"🎬 BATCH THUMBNAIL EXTRACTION")
    print(f"   Channels to process: {len(CHANNELS_TO_ANALYZE)}")
    print(f"   Max videos per channel: {MAX_VIDEOS}")
    print(f"   Min duration: {MIN_DURATION_MIN} minutes")
    print(f"   AI Analysis: {'Disabled' if SKIP_AI_ANALYSIS else 'Enabled'}")
    print("=" * 60)

    for i, channel in enumerate(CHANNELS_TO_ANALYZE, 1):
        print(f"\n{'='*60}")
        print(f"📺 Processing channel {i}/{len(CHANNELS_TO_ANALYZE)}: {channel}")
        print(f"{'='*60}")

        try:
            main(
                channel_input=channel,
                max_videos=MAX_VIDEOS,
                days_back=DAYS_BACK,
                skip_ai_analysis=SKIP_AI_ANALYSIS,
                min_duration_minutes=MIN_DURATION_MIN
            )
        except Exception as e:
            print(f"\n❌ Error processing {channel}: {e}")
            print("   Continuing to next channel...\n")
            continue

    print("\n" + "=" * 60)
    print("✅ BATCH PROCESSING COMPLETE")
    print(f"   Processed {len(CHANNELS_TO_ANALYZE)} channels")
    print(f"   Data saved to: thumbnail_data/")
    print("=" * 60)
