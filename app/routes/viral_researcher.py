"""
Viral Researcher & Scripter Routes

Handles all routes for the viral video research and script generation module.
"""
from fastapi import APIRouter, Request, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from typing import List, Optional
import logging
import json

from app.services.creator_profile_service import CreatorProfileService
from app.services.viral_video_service import ViralVideoService
from app.services.transcript_service import TranscriptService
from app.services.angle_generator_service import AngleGeneratorService
from app.services.research_service import ResearchService
from app.services.research_synthesis_service import ResearchSynthesisService
from app.services.script_generator_service import ScriptGeneratorService
from app.services.supabase_client import get_supabase_client
from app.utils.session import get_current_user
from app.services.angle_cache_service import AngleCacheService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/viral-researcher", tags=["viral-researcher"])


# ============================================================================
# Helper Functions
# ============================================================================

async def require_creator_profile(request: Request):
    """Middleware to ensure user has a creator profile."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    profile_service = CreatorProfileService()
    has_profile = profile_service.profile_exists(user['user_id'])
    
    logger.info(f"Checking profile for user {user['user_id']}: Exists={has_profile}")

    if not has_profile:
        logger.warning(f"User {user['user_id']} blocked: No creator profile found")
        # Check what tables exist to debug
        # profile_service.debug_tables() 
        raise HTTPException(
            status_code=403,
            detail="Creator profile required. Please create your profile first."
        )

    return user


# ============================================================================
# Main Pages
# ============================================================================

@router.get("/", response_class=HTMLResponse)
async def viral_researcher_home(request: Request):
    """Main landing page for Viral Researcher & Scripter."""
    user = await require_creator_profile(request)

    # Get list of previously scraped channels
    video_service = ViralVideoService()
    channels = video_service.get_all_channels()

    return request.app.state.templates.TemplateResponse(
        "viral_researcher_home.html",
        {
            "request": request,
            "user": user,
            "channels": channels,
            "has_profile": True
        }
    )


@router.post("/scrape")
async def scrape_channels(
    request: Request,
    channel_input: str = Form(...),
    force_refresh: bool = Form(False)
):
    """
    Scrape YouTube channels for viral video analysis.

    Args:
        channel_input: Comma or newline separated channel handles/URLs
        force_refresh: Force re-scraping even if channel exists
    """
    user = await require_creator_profile(request)

    # Parse channel inputs
    channels = [
        ch.strip()
        for ch in channel_input.replace('\n', ',').split(',')
        if ch.strip()
    ]

    if not channels:
        raise HTTPException(status_code=400, detail="No channels provided")

    video_service = ViralVideoService()
    results = []

    for channel in channels:
        try:
            result = video_service.scrape_channel(channel, days=365, force_refresh=force_refresh)
            results.append(result)
        except Exception as e:
            logger.error(f"Error scraping channel {channel}: {e}")
            results.append({
                'success': False,
                'channel_id': None,
                'error': str(e)
            })

    return request.app.state.templates.TemplateResponse(
        "components/scrape_results.html",
        {
            "request": request,
            "results": results
        }
    )


@router.get("/videos/{channel_id}", response_class=HTMLResponse)
async def list_videos(request: Request, channel_id: str, bucket: Optional[str] = None):
    """Display videos organized by view buckets."""
    user = await require_creator_profile(request)

    video_service = ViralVideoService()

    # Get bucket statistics
    bucket_stats = video_service.get_bucket_stats(channel_id)

    # Get videos (filtered by bucket if specified)
    videos = video_service.get_videos_by_bucket(channel_id, bucket)

    # Get channel info
    channels = video_service.get_all_channels()
    channel_info = next((c for c in channels if c['channel_id'] == channel_id), None)

    return request.app.state.templates.TemplateResponse(
        "viral_videos_list.html",
        {
            "request": request,
            "user": user,
            "channel_id": channel_id,
            "channel_name": channel_info['channel_name'] if channel_info else channel_id,
            "bucket_stats": bucket_stats,
            "videos": videos,
            "selected_bucket": bucket
        }
    )


@router.get("/video/{video_id}", response_class=HTMLResponse)
async def video_details(request: Request, video_id: str):
    """Display video details with transcript (lazy loaded)."""
    user = await require_creator_profile(request)

    video_service = ViralVideoService()
    video = video_service.get_video_details(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check if transcript exists
    has_transcript = video.get('transcript') is not None

    return request.app.state.templates.TemplateResponse(
        "video_details.html",
        {
            "request": request,
            "user": user,
            "video": video,
            "has_transcript": has_transcript
        }
    )


@router.post("/video/{video_id}/fetch-transcript")
async def fetch_transcript(request: Request, video_id: str):
    """Fetch transcript for a video (AJAX endpoint)."""
    user = await require_creator_profile(request)

    transcript_service = TranscriptService()

    try:
        transcript = transcript_service.fetch_transcript(video_id)

        if transcript:
            # Trigger page reload to update UI state (sidebar, buttons, etc.)
            return Response(headers={"HX-Refresh": "true"})
        else:
            return JSONResponse(
                content={
                    'success': False,
                    'error': 'Unable to fetch transcript. Video may not have captions.'
                },
                status_code=500
            )

    except Exception as e:
        logger.error(f"Error fetching transcript: {e}")
        return JSONResponse(
            content={'success': False, 'error': str(e)},
            status_code=500
        )


@router.post("/video/{video_id}/generate-angles")
async def generate_angles(request: Request, video_id: str):
    """Generate creative angles for a video."""
    user = await require_creator_profile(request)

    # Get video data
    video_service = ViralVideoService()
    video = video_service.get_video_details(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Ensure transcript exists
    if not video.get('transcript'):
        raise HTTPException(status_code=400, detail="Transcript required. Please fetch transcript first.")

    # Get user profile
    profile_service = CreatorProfileService()
    profile = profile_service.get_user_profile(user['user_id'])

    # Generate angles
    angle_service = AngleGeneratorService()
    angles = angle_service.generate_angles(video, profile, video['transcript'])

    # Cache angles
    cache_service = AngleCacheService()
    cache_service.save_angles(video_id, angles)

    return request.app.state.templates.TemplateResponse(
        "components/angle_list.html",
        {
            "request": request,
            "angles": angles,
            "video_id": video_id
        }
    )


@router.get("/angle-selection", response_class=HTMLResponse)
async def angle_selection(request: Request, video_id: str, angle_index: int):
    """Display selected angle for confirmation."""
    user = await require_creator_profile(request)

    video_service = ViralVideoService()
    video = video_service.get_video_details(video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Get angles from cache
    cache_service = AngleCacheService()
    selected_angle = cache_service.get_angle_by_index(video_id, angle_index)
    other_angles = [a for i, a in enumerate(cache_service.get_angles(video_id)) if i != angle_index]

    if not selected_angle:
        # Fallback if cache expired or invalid index
        # For now, redirect back to video details
        return RedirectResponse(url=f"/viral-researcher/video/{video_id}", status_code=303)

    return request.app.state.templates.TemplateResponse(
        "angle_selection.html",
        {
            "request": request,
            "user": user,
            "video": video,
            "selected_angle": selected_angle,
            "other_angles": other_angles,
            "angle_index": angle_index
        }
    )


@router.post("/generate-script")
async def generate_script(
    request: Request,
    video_id: str = Form(...),
    angle_index: int = Form(...)
):
    """Generate complete script with research."""
    user = await require_creator_profile(request)

    # Get angle from cache using index
    cache_service = AngleCacheService()
    angle = cache_service.get_angle_by_index(video_id, angle_index)

    if not angle:
        raise HTTPException(status_code=400, detail="Selected angle not found or expired. Please regenerate angles.")

    # Get video data
    video_service = ViralVideoService()
    video = video_service.get_video_details(video_id)

    if not video or not video.get('transcript'):
        raise HTTPException(status_code=400, detail="Video or transcript not found")

    # Get user profile
    profile_service = CreatorProfileService()
    profile = profile_service.get_user_profile(user['user_id'])

    try:
        # Step 1: Gather research
        research_service = ResearchService()
        claims = research_service.extract_claims_from_transcript(video['transcript'])

        raw_research = research_service.gather_research(
            video_topic=video['title'],
            niche=profile.get('niche', 'General'),
            transcript_summary=video['transcript'][:1000],
            claims=claims
        )

        # Step 2: Synthesize research (Gemini)
        synthesis_service = ResearchSynthesisService()
        research_brief = synthesis_service.synthesize_research(
            video_data=video,
            selected_angle=angle,
            raw_research=raw_research,
            profile=profile
        )

        # Step 3: Generate script (Claude)
        script_service = ScriptGeneratorService()
        result = script_service.generate_script(
            video_data=video,
            selected_angle=angle,
            research_brief=research_brief,
            profile=profile
        )

        # Step 4: Save to database
        supabase = get_supabase_client()

        # Prepare angles for storage (all angles generated, not just selected)
        # We'll need to pass this from the frontend, but for now just store selected
        script_data = {
            'user_id': user['user_id'],
            'original_video_id': video_id,
            'selected_angle': angle.get('angle_name'),
            'angle_options': json.dumps([angle]),  # Store as JSONB
            'script': result['script'],
            'titles': result['titles'],
            'thumbnail_descriptions': result['thumbnails'],
            'research_data': json.dumps({
                'raw_research': raw_research,
                'research_brief': research_brief
            })
        }

        response = supabase.table('generated_scripts').insert(script_data).execute()

        if response.data and len(response.data) > 0:
            script_id = response.data[0]['id']

            return JSONResponse(content={
                'success': True,
                'script_id': script_id,
                'redirect_url': f'/viral-researcher/script/{script_id}'
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to save script")

    except Exception as e:
        logger.error(f"Error generating script: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/script/{script_id}", response_class=HTMLResponse)
async def view_script(request: Request, script_id: int):
    """Display generated script with titles and thumbnails."""
    user = await require_creator_profile(request)

    supabase = get_supabase_client()

    # Get script data
    response = (
        supabase.table('generated_scripts')
        .select('*')
        .eq('id', script_id)
        .eq('user_id', user['user_id'])  # Security: ensure user owns this script
        .execute()
    )

    if not response.data or len(response.data) == 0:
        raise HTTPException(status_code=404, detail="Script not found")

    script_data = response.data[0]

    # Parse JSON fields
    try:
        research_data = json.loads(script_data['research_data']) if isinstance(script_data['research_data'], str) else script_data['research_data']
        research_brief = research_data.get('research_brief', {})
        
        angle_options = json.loads(script_data['angle_options']) if isinstance(script_data['angle_options'], str) else script_data['angle_options']
        # Find the specific angle used
        selected_angle_name = script_data['selected_angle']
        angle_used = next((a for a in angle_options if a['angle_name'] == selected_angle_name), angle_options[0] if angle_options else {})
    except Exception as e:
        logger.error(f"Error parsing script JSON data: {e}")
        research_brief = {}
        angle_used = {}

    # Get original video data for source info
    video_service = ViralVideoService()
    video = video_service.get_video_details(script_data['original_video_id'])
    
    # Format script
    script_service = ScriptGeneratorService()
    formatted_script = script_service.format_script_for_display(script_data['script'])
    
    # Calculate stats
    word_count = len(script_data['script'].split())
    est_minutes = round(word_count / 150) # Approx 150 wpm
    
    # Construct rich context object
    script_context = {
        **script_data,
        'selected_title': script_data['titles'][0] if script_data.get('titles') else 'Untitled Script',
        'selected_title_index': 0,
        'title_options': script_data.get('titles', []),
        'selected_thumbnail_index': 0,
        'thumbnail_options': script_data.get('thumbnail_descriptions', []),
        
        # Computed
        'formatted_script': formatted_script,
        'word_count': word_count,
        'estimated_duration': f"{est_minutes} min",
        'created_ago': "Just now", # TODO: Implement real relative time or format date
        
        # Source Info
        'source_video_title': video.get('title', 'Unknown Video') if video else 'Unknown Video',
        'source_video_thumbnail': video.get('thumbnail_url', '') if video else '',
        'source_channel_name': video.get('channel_name', 'Unknown Channel') if video else 'Unknown Channel',
        'source_view_count_formatted': f"{int(video.get('view_count', 0)):,}" if video else '0',
        'source_view_bucket': 'Viral', # Simplified, calculate if needed
        'source_video_url': f"https://www.youtube.com/watch?v={script_data['original_video_id']}",
        
        # Research & Angle
        'research_brief': research_brief,
        'angle_name': angle_used.get('angle_name', 'Custom'),
        'core_hook': angle_used.get('core_hook', ''),
        'target_emotion': angle_used.get('target_emotion', 'Neutral'),
        'estimated_appeal': angle_used.get('estimated_appeal', 'Unknown')
    }

    return request.app.state.templates.TemplateResponse(
        "script_output.html",
        {
            "request": request,
            "user": user,
            "script": script_context  # Renamed from script_data to match template
        }
    )


@router.get("/my-scripts", response_class=HTMLResponse)
async def my_scripts(request: Request):
    """List all scripts generated by the user."""
    user = await require_creator_profile(request)

    supabase = get_supabase_client()

    response = (
        supabase.table('generated_scripts')
        .select('id, created_at, selected_angle, original_video_id')
        .eq('user_id', user['user_id'])
        .order('created_at', desc=True)
        .execute()
    )

    scripts = response.data if response.data else []

    return request.app.state.templates.TemplateResponse(
        "my_scripts.html",
        {
            "request": request,
            "user": user,
            "scripts": scripts
        }
    )
