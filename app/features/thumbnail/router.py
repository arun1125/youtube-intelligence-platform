from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import logging
import random
import uuid
from typing import Optional, List, Dict
from datetime import datetime

from app.core.config import get_settings
from .ai_service import AIService
from .youtube_service import YouTubeService
from .data_service import DataService
from app.core.database import supabase_client
from app.features.auth.auth_service import auth_service
from app.middleware.auth import optional_auth, require_auth
from app.utils.channel_resolver import resolve_channels_parallel
from app.utils.helpers import (
    save_uploaded_file,
    format_duration,
    format_view_count,
    format_time_ago,
    is_shorts
)
from app.models.schemas import VideoData

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# In-memory session storage for shuffle functionality
# In production, use Redis or a database
sessions = {}


@router.get("/thumbnail-tester", response_class=HTMLResponse)
async def index(request: Request, user_id: Optional[str] = Depends(optional_auth())):
    """Render the thumbnail tester page with input form."""
    user = None

    if user_id:
        try:
            # Get user info using access token (not admin API)
            from app.utils.session import get_access_token
            access_token = get_access_token(request)

            if access_token:
                user_response = supabase_client.auth.get_user(access_token)
                profile_response = supabase_client.table("profiles").select("*").eq("id", user_id).single().execute()

                if user_response.user and profile_response.data:
                    user = {
                        "email": user_response.user.email,
                        "full_name": profile_response.data.get("full_name"),
                        "avatar_url": profile_response.data.get("avatar_url")
                    }
        except Exception as e:
            logger.warning(f"Failed to get user info: {e}")

    # Load most recent test for authenticated users
    recent_test_html = None
    if user_id:
        try:
            logger.info(f"Loading most recent test for user {user_id}")
            # Get most recent completed test
            test_response = supabase_client.table("thumbnail_tests").select(
                "*"
            ).eq("user_id", user_id).eq("status", "completed").order(
                "created_at", desc=True
            ).limit(1).execute()

            logger.info(f"Found {len(test_response.data) if test_response.data else 0} tests")

            if test_response.data and len(test_response.data) > 0:
                test = test_response.data[0]
                test_id = test["id"]

                # Fetch videos for this test
                test_videos_response = supabase_client.table("test_videos").select(
                    "*, youtube_videos(*)"
                ).eq("test_id", test_id).order("position").execute()

                if test_videos_response.data:
                    # Build video data
                    videos = []
                    for tv in test_videos_response.data:
                        vid = tv["youtube_videos"]
                        if vid:
                            video_data = {
                                "video_id": vid["video_id"],
                                "title": vid["title"] if not tv["is_user_video"] else test["video_title"],
                                "channel_name": "Your Channel" if tv["is_user_video"] else vid.get("channel_name", "Unknown"),
                                "channel_id": vid["channel_id"],
                                "thumbnail_url": f"/{test['thumbnail_path']}" if tv["is_user_video"] else vid["thumbnail_url"],
                                "view_count": vid.get("view_count"),
                                "published_at": vid.get("published_at"),
                                "duration_seconds": vid.get("duration_seconds"),
                                "video_url": f"https://youtube.com/watch?v={vid['video_id']}" if not tv["is_user_video"] else "#",
                                "is_user_video": tv["is_user_video"],
                                "duration": format_duration(vid.get("duration_seconds")),
                                "view_text": format_view_count(vid.get("view_count")),
                                "time_ago": format_time_ago(vid.get("published_at")),
                                "channel_avatar": f"/{test['avatar_path']}" if (tv["is_user_video"] and test.get("avatar_path")) else None
                            }
                            videos.append(video_data)

                    # Render the grid HTML
                    recent_test_html = templates.get_template("thumbnail/components/video_grid.html").render(
                        videos=videos,
                        video_count=len(videos),
                        session_id=test_id
                    )
                    logger.info(f"✓ Successfully loaded recent test with {len(videos)} videos")
        except Exception as e:
            logger.error(f"Failed to load recent test: {e}", exc_info=True)

    return templates.TemplateResponse("thumbnail/index.html", {
        "request": request,
        "user": user,
        "recent_test_html": recent_test_html
    })


@router.get("/preview/{test_id}", response_class=HTMLResponse)
async def view_preview(
    request: Request,
    test_id: str,
    user_id: Optional[str] = Depends(optional_auth())
):
    """View a test preview in the mixed grid format."""
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Get the test
        test_response = supabase_client.table("thumbnail_tests").select(
            "*"
        ).eq("id", test_id).eq("user_id", user_id).single().execute()

        if not test_response.data:
            raise HTTPException(status_code=404, detail="Test not found")

        test = test_response.data

        # Fetch videos for this test
        test_videos_response = supabase_client.table("test_videos").select(
            "*, youtube_videos(*)"
        ).eq("test_id", test_id).order("position").execute()

        videos = []
        if test_videos_response.data:
            for tv in test_videos_response.data:
                vid = tv.get("youtube_videos")
                if vid:
                    try:
                        video_data = {
                            "video_id": vid["video_id"],
                            "title": test["video_title"] if tv["is_user_video"] else vid["title"],
                            "channel_name": "Your Channel" if tv["is_user_video"] else vid.get("channel_name", "Unknown"),
                            "channel_id": vid["channel_id"],
                            "thumbnail_url": f"/{test['thumbnail_path']}" if tv["is_user_video"] else vid["thumbnail_url"],
                            "view_count": vid.get("view_count"),
                            "published_at": vid.get("published_at"),
                            "duration_seconds": vid.get("duration_seconds"),
                            "video_url": f"https://youtube.com/watch?v={vid['video_id']}" if not tv["is_user_video"] else "#",
                            "is_user_video": tv["is_user_video"],
                            "duration": format_duration(vid.get("duration_seconds") or 0),
                            "view_text": format_view_count(vid.get("view_count")),
                            "time_ago": format_time_ago(vid.get("published_at")) if vid.get("published_at") else "Recently",
                            "channel_avatar": f"/{test['avatar_path']}" if (tv["is_user_video"] and test.get("avatar_path")) else None
                        }
                        videos.append(video_data)
                    except Exception as e:
                        logger.error(f"Error formatting video {vid.get('video_id')}: {e}", exc_info=True)

        # Get user info for header
        user = None
        if user_id:
            try:
                from app.utils.session import get_access_token
                access_token = get_access_token(request)

                if access_token:
                    user_response = supabase_client.auth.get_user(access_token)
                    profile_response = supabase_client.table("profiles").select("*").eq("id", user_id).single().execute()

                    if user_response.user and profile_response.data:
                        user = {
                            "email": user_response.user.email,
                            "full_name": profile_response.data.get("full_name"),
                            "avatar_url": profile_response.data.get("avatar_url")
                        }
            except Exception as e:
                logger.warning(f"Failed to get user info: {e}")

        # Render the grid HTML
        video_grid_html = templates.get_template("thumbnail/components/video_grid.html").render(
            videos=videos,
            video_count=len(videos),
            session_id=test_id
        )

        return templates.TemplateResponse("thumbnail/index.html", {
            "request": request,
            "user": user,
            "recent_test_html": video_grid_html
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load preview")


@router.post("/generate")
async def generate_preview(
    persona: str = Form(...),
    title: str = Form(...),
    thumbnail: UploadFile = File(...),
    avatar: Optional[UploadFile] = File(None),
    user_id: Optional[str] = Depends(optional_auth())
):
    """
    Main workflow: Generate thumbnail preview in competitor context.

    Flow:
    1. Check if user can create test (usage limits)
    2. AI generates 10 channel suggestions based on persona
    3. Resolve channel handles to IDs (parallel)
    4. Fetch 5 recent videos per channel via YouTube API
    5. Save test and videos to database
    6. Filter out Shorts for display
    7. Inject user's video
    8. Shuffle and render grid
    9. Increment usage counter
    """
    try:
        # Check if user is authenticated
        if not user_id:
            logger.warning("Unauthenticated user attempted to generate preview")
            return HTMLResponse(
                content="""
                <div class="bg-red-900 border border-red-700 rounded-lg p-6 text-center">
                    <svg class="w-16 h-16 mx-auto mb-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <h2 class="text-2xl font-bold mb-2 text-red-400">Authentication Required</h2>
                    <p class="text-red-200 mb-6">You need to be signed in to generate thumbnail previews.</p>
                    <a href="/auth/login" class="inline-block bg-yt-accent hover:bg-blue-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors">
                        Sign In to Continue
                    </a>
                </div>
                """,
                status_code=200
            )

        logger.info(f"📝 New request from user {user_id} - Persona: {persona[:50]}...")

        # Step 1: Check if user can create test
        can_create = auth_service.can_create_test(user_id)
        if not can_create:
            logger.warning(f"User {user_id} hit usage limit")
            return HTMLResponse(
                content="""
                <div class="bg-yellow-900 border border-yellow-700 rounded-lg p-6 text-center">
                    <svg class="w-16 h-16 mx-auto mb-4 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h2 class="text-2xl font-bold mb-2 text-yellow-400">Monthly Limit Reached</h2>
                    <p class="text-yellow-200 mb-6">You've used all 5 free tests this month. Upgrade to Pro for unlimited tests!</p>
                    <a href="/api/payment/upgrade" class="inline-block bg-yt-accent hover:bg-blue-600 text-white font-semibold py-3 px-6 rounded-lg transition-colors">
                        Upgrade to Pro
                    </a>
                </div>
                """,
                status_code=200
            )

        # Initialize services
        ai_service = AIService()
        youtube_service = YouTubeService()
        data_service = DataService()

        # Step 1: Get channel suggestions from AI
        logger.info("🤖 Getting channel suggestions from AI...")
        channel_handles = ai_service.get_channel_suggestions(
            persona=persona,
            num_channels=settings.max_channels
        )

        if not channel_handles:
            raise HTTPException(
                status_code=500,
                detail="Failed to get channel suggestions from AI"
            )

        logger.info(f"✓ Got {len(channel_handles)} channel suggestions")

        # Step 2: Resolve channel handles to IDs (parallel)
        logger.info("🔍 Resolving channel IDs (parallel)...")
        resolved_channels = resolve_channels_parallel(
            channel_handles=channel_handles,
            max_workers=settings.max_workers
        )

        # Filter successful resolutions
        successful_channels = [ch for ch in resolved_channels if ch['success']]

        if not successful_channels:
            raise HTTPException(
                status_code=500,
                detail="Failed to resolve any channel IDs"
            )

        logger.info(f"✓ Successfully resolved {len(successful_channels)}/{len(channel_handles)} channels")

        # Step 3: Fetch videos from channels
        logger.info("📺 Fetching videos from YouTube API...")
        all_videos = youtube_service.get_videos_for_channels(
            channel_data=successful_channels,
            videos_per_channel=settings.videos_per_channel
        )

        if not all_videos:
            raise HTTPException(
                status_code=500,
                detail="Failed to fetch videos from channels"
            )

        logger.info(f"✓ Fetched {len(all_videos)} total videos")

        # Step 4: Log ALL videos to CSV (including Shorts)
        logger.info("💾 Logging videos to CSV...")
        channel_id_to_handle = {ch['channel_id']: ch['handle'] for ch in successful_channels}
        logged_count = data_service.log_videos_to_csv(
            videos=all_videos,
            persona=persona,
            channel_handles=channel_id_to_handle
        )

        logger.info(f"✓ Logged {logged_count} videos to CSV")

        # Step 5: Handle uploaded files (BEFORE database save!)
        logger.info("📸 Processing uploaded files...")
        thumbnail_path = save_uploaded_file(
            file_data=await thumbnail.read(),
            filename=thumbnail.filename,
            upload_dir=settings.upload_dir
        )

        avatar_path = None
        if avatar and avatar.filename:
            avatar_path = save_uploaded_file(
                file_data=await avatar.read(),
                filename=avatar.filename,
                upload_dir=settings.upload_dir
            )

        # Step 6: Save test to database
        logger.info("💾 Saving test to database...")

        # Create test record
        test_data = {
            "user_id": user_id,
            "persona": persona,
            "video_title": title,
            "thumbnail_path": thumbnail_path,
            "avatar_path": avatar_path if avatar_path else None,
            "total_videos_fetched": len(all_videos),
            "channels_discovered": [f"@{ch}" for ch in successful_channels],
            "status": "completed",
            "completed_at": "now()"
        }

        test_response = supabase_client.table("thumbnail_tests").insert(test_data).execute()
        test_id = test_response.data[0]["id"]
        logger.info(f"✓ Test saved with ID: {test_id}")

        # Step 7: Save all videos to database
        logger.info("💾 Saving videos to database...")

        # First, extract and upsert unique channels
        unique_channels = {}
        for video in all_videos:
            if video.channel_id not in unique_channels:
                unique_channels[video.channel_id] = {
                    "channel_id": video.channel_id,
                    "channel_name": video.channel_name,
                    "channel_handle": channel_id_to_handle.get(video.channel_id, ""),
                }

        if unique_channels:
            channel_inserts = list(unique_channels.values())
            try:
                supabase_client.table("youtube_channels").upsert(
                    channel_inserts,
                    on_conflict="channel_id"
                ).execute()
                logger.info(f"✓ Upserted {len(channel_inserts)} channels to youtube_channels table")
            except Exception as e:
                # RLS may block insert if channels already exist from another user's test
                # This is expected behavior - the channels are shared across users
                # Log at debug level since this is a normal occurrence
                logger.debug(f"Channel upsert skipped (likely RLS - channels may already exist): {e}")

        # Second, upsert videos into youtube_videos table
        youtube_video_inserts = []
        for video in all_videos:
            youtube_video_data = {
                "video_id": video.video_id,
                "channel_id": video.channel_id,
                "title": video.title,
                "thumbnail_url": video.thumbnail_url,
                "view_count": video.view_count,
                "published_at": video.published_at,
                "duration_seconds": video.duration_seconds,
                "is_short": is_shorts(video.duration_seconds, settings.shorts_duration_threshold)
            }
            youtube_video_inserts.append(youtube_video_data)

        if youtube_video_inserts:
            # Upsert videos (insert or update if exists)
            youtube_response = supabase_client.table("youtube_videos").upsert(
                youtube_video_inserts,
                on_conflict="video_id"
            ).execute()
            logger.info(f"✓ Upserted {len(youtube_video_inserts)} videos to youtube_videos table")

            # Create mapping of video_id to UUID
            video_id_to_uuid = {v["video_id"]: v["id"] for v in youtube_response.data}

        # Step 7.5: Save user's video to database FIRST (before test_videos)
        logger.info("💾 Saving user video to database...")
        user_video_id = f"user_video_{test_id}"
        user_channel_id = f"user_channel_{user_id}"

        # Insert user channel (used to store user's test videos)
        try:
            supabase_client.table("youtube_channels").upsert([{
                "channel_id": user_channel_id,
                "channel_name": "Your Channel",
                "channel_handle": "@user"
            }], on_conflict="channel_id").execute()
            logger.debug(f"✓ User channel upserted: {user_channel_id}")
        except Exception as e:
            # User channel may already exist from a previous test - this is fine
            logger.debug(f"User channel upsert skipped (likely already exists): {e}")

        # Insert user video
        # User videos don't have a real duration yet - use None to indicate "unknown"
        # The template will handle None gracefully (won't show duration badge)
        user_video_db = {
            "video_id": user_video_id,
            "channel_id": user_channel_id,
            "title": title,
            "thumbnail_url": thumbnail_path,  # Store without leading slash
            "view_count": None,
            "published_at": datetime.now().isoformat(),
            "duration_seconds": None,  # User video - duration unknown
            "is_short": False
        }

        user_video_response = supabase_client.table("youtube_videos").upsert(
            [user_video_db],
            on_conflict="video_id"
        ).execute()
        user_video_uuid = user_video_response.data[0]["id"]

        # Step 7.6: Build ordered list with user video mixed in
        # Filter out shorts
        non_shorts = [v for v in all_videos if not is_shorts(v.duration_seconds, settings.shorts_duration_threshold)]

        # Shuffle the non-shorts
        random.shuffle(non_shorts)

        # Calculate where to insert user video (in top 2/3)
        total_videos = len(non_shorts) + 1
        top_two_thirds = int(total_videos * 2 / 3)
        user_position = random.randint(0, max(0, top_two_thirds - 1))

        # Insert all test_videos with correct positions
        test_video_inserts = []
        current_position = 0

        for video in non_shorts:
            # If we've reached the user position, skip it (we'll add user video there)
            if current_position == user_position:
                current_position += 1

            test_video_data = {
                "test_id": test_id,
                "video_id": video_id_to_uuid[video.video_id],
                "position": current_position,
                "is_user_video": False
            }
            test_video_inserts.append(test_video_data)
            current_position += 1

        # Add user video at the designated position
        test_video_inserts.append({
            "test_id": test_id,
            "video_id": user_video_uuid,
            "position": user_position,
            "is_user_video": True
        })

        # Insert all at once
        supabase_client.table("test_videos").insert(test_video_inserts).execute()
        logger.info(f"✓ Saved {len(test_video_inserts)} video references (including user video at position {user_position})")

        # Step 8: Filter out Shorts for DISPLAY only (keep in CSV)
        display_videos = [
            video for video in all_videos
            if not is_shorts(video.duration_seconds, settings.shorts_duration_threshold)
        ]

        logger.info(f"✓ Filtered to {len(display_videos)} non-Short videos for display")

        # Step 9: Create user video object
        user_video_data = {
            'video_id': 'user_video',
            'title': title,
            'channel_name': 'Your Channel',
            'channel_id': 'user_channel',
            'thumbnail_url': f"/{thumbnail_path}",
            'view_count': None,
            'published_at': datetime.now().isoformat(),
            'duration_seconds': None,  # User video - duration unknown
            'video_url': '#',
            'is_user_video': True,
            'channel_avatar': f"/{avatar_path}" if avatar_path else None
        }

        # Step 10: Shuffle competitor videos first
        random.shuffle(display_videos)

        # Insert user video in top 2/3 of results
        total_videos = len(display_videos) + 1
        top_two_thirds = int(total_videos * 2 / 3)
        # Random position within top 2/3
        user_position = random.randint(0, max(0, top_two_thirds - 1))

        # Insert user video at calculated position
        all_display_videos = display_videos[:user_position] + [user_video_data] + display_videos[user_position:]

        # Step 11: Format videos for template
        formatted_videos = format_videos_for_template(all_display_videos)

        # Step 12: Store session for shuffle functionality
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            'videos': all_display_videos,
            'created_at': datetime.now()
        }

        logger.info(f"✅ Successfully generated preview with {len(formatted_videos)} videos")

        # Step 13: Increment usage counter
        auth_service.increment_test_usage(user_id)
        logger.info(f"✓ Incremented usage counter for user {user_id}")

        # Redirect to the preview page
        return RedirectResponse(url=f"/preview/{test_id}", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in generate_preview: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.patch("/test/{test_id}/title")
async def update_test_title(
    test_id: str,
    title: str = Form(...),
    user_id: Optional[str] = Depends(optional_auth())
):
    """
    Update the video title for a test.
    """
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Verify test belongs to user
        test_response = supabase_client.table("thumbnail_tests").select("id").eq(
            "id", test_id
        ).eq("user_id", user_id).single().execute()

        if not test_response.data:
            raise HTTPException(status_code=404, detail="Test not found")

        # Update the title
        update_response = supabase_client.table("thumbnail_tests").update({
            "video_title": title
        }).eq("id", test_id).execute()

        logger.info(f"✓ Updated title for test {test_id}")

        return {"success": True, "title": title}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating title: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update title: {str(e)}")


@router.post("/shuffle", response_class=HTMLResponse)
async def shuffle_results(
    request: Request,
    session_id: str = Form(...),
    user_id: Optional[str] = Depends(optional_auth())
):
    """
    Shuffle existing results without re-fetching data.

    Uses in-memory session storage OR fetches from database if not in memory.
    """
    try:
        logger.info(f"🔀 Shuffling session: {session_id}")

        all_videos = []

        # Try in-memory session first (for freshly generated previews)
        if session_id in sessions:
            session_data = sessions[session_id]
            all_videos = session_data['videos']
            logger.info(f"✓ Found session in memory")
        else:
            # Session not in memory, fetch from database (for loaded previews)
            logger.info(f"✓ Session not in memory, fetching from database")

            if not user_id:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Get the test
            test_response = supabase_client.table("thumbnail_tests").select(
                "*"
            ).eq("id", session_id).eq("user_id", user_id).single().execute()

            if not test_response.data:
                raise HTTPException(status_code=404, detail="Test not found")

            test = test_response.data

            # Fetch videos for this test
            test_videos_response = supabase_client.table("test_videos").select(
                "*, youtube_videos(*)"
            ).eq("test_id", session_id).order("position").execute()

            if not test_videos_response.data:
                raise HTTPException(status_code=404, detail="No videos found for this test")

            # Build video data list
            for tv in test_videos_response.data:
                vid = tv.get("youtube_videos")
                if vid:
                    video_data = {
                        "video_id": vid["video_id"],
                        "title": test["video_title"] if tv["is_user_video"] else vid["title"],
                        "channel_name": "Your Channel" if tv["is_user_video"] else vid.get("channel_name", "Unknown"),
                        "channel_id": vid["channel_id"],
                        "thumbnail_url": f"/{test['thumbnail_path']}" if tv["is_user_video"] else vid["thumbnail_url"],
                        "view_count": vid.get("view_count"),
                        "published_at": vid.get("published_at"),
                        "duration_seconds": vid.get("duration_seconds"),
                        "video_url": f"https://youtube.com/watch?v={vid['video_id']}" if not tv["is_user_video"] else "#",
                        "is_user_video": tv["is_user_video"],
                        "channel_avatar": f"/{test['avatar_path']}" if (tv["is_user_video"] and test.get("avatar_path")) else None
                    }
                    all_videos.append(video_data)

            logger.info(f"✓ Loaded {len(all_videos)} videos from database")

        if not all_videos:
            raise HTTPException(status_code=404, detail="No videos found to shuffle")

        # Separate user video from competitors
        user_video = None
        competitor_videos = []
        for video in all_videos:
            if isinstance(video, dict) and video.get('is_user_video'):
                user_video = video
            else:
                competitor_videos.append(video)

        # Shuffle competitor videos
        random.shuffle(competitor_videos)

        # Insert user video in top 2/3 of results
        if user_video:
            total_videos = len(competitor_videos) + 1
            top_two_thirds = int(total_videos * 2 / 3)
            user_position = random.randint(0, max(0, top_two_thirds - 1))
            shuffled_videos = competitor_videos[:user_position] + [user_video] + competitor_videos[user_position:]
        else:
            shuffled_videos = competitor_videos

        # Format for template
        formatted_videos = format_videos_for_template(shuffled_videos)

        logger.info(f"✅ Shuffled {len(formatted_videos)} videos")

        # Render video grid
        return templates.TemplateResponse(
            "thumbnail/components/video_grid.html",
            {
                "request": request,
                "videos": formatted_videos,
                "video_count": len(formatted_videos),
                "session_id": session_id
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in shuffle_results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Shuffle error: {str(e)}")


def format_videos_for_template(videos: List[Dict]) -> List[Dict]:
    """
    Format video data for template rendering.

    Adds formatted strings for views, duration, and time ago.
    """
    formatted = []

    for video in videos:
        # Handle both VideoData objects and dicts
        if isinstance(video, VideoData):
            video = video.model_dump()

        formatted_video = {
            'video_id': video.get('video_id'),
            'title': video.get('title'),
            'channel_name': video.get('channel_name'),
            'thumbnail_url': video.get('thumbnail_url'),
            'video_url': video.get('video_url', '#'),
            'is_user_video': video.get('is_user_video', False),
            'channel_avatar': video.get('channel_avatar'),
            'duration': format_duration(video.get('duration_seconds', 0)),
            'view_text': format_view_count(video.get('view_count')),
            'time_ago': format_time_ago(video.get('published_at', ''))
        }

        formatted.append(formatted_video)

    return formatted


# Cleanup old sessions periodically (basic implementation)
# In production, use Redis with TTL
@router.on_event("startup")
async def cleanup_sessions():
    """Cleanup old sessions on startup."""
    logger.info("🧹 Session cleanup initialized")
