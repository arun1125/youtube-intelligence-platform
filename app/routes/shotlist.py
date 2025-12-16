"""
Shot List routes - Video production planning tool.
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import logging
from typing import Optional
from pydantic import UUID4

from app.middleware.auth import require_auth
from app.services.shotlist_service import shotlist_service
from app.models.database import ProductionProjectCreate, ProductionVideoCreate

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")

router = APIRouter(tags=["shotlist"])


# ============================================
# PAGE ROUTES (HTML)
# ============================================

@router.get("/shotlist", response_class=HTMLResponse)
async def shotlist_dashboard(
    request: Request,
    user_id: str = Depends(require_auth()),
    project_id: Optional[str] = None
):
    """
    Shot list dashboard - Shows all projects and videos.
    """
    try:
        # Get user's projects
        projects = shotlist_service.get_user_projects(user_id)

        # Get user's videos (optionally filtered by project)
        videos = shotlist_service.get_user_videos(user_id, project_id)

        # Get user info from session
        from app.utils.session import get_session_data, get_access_token
        from app.services.supabase_client import supabase_client

        access_token = get_access_token(request)
        profile_response = supabase_client.table("profiles").select("*").eq("id", user_id).single().execute()
        profile = profile_response.data

        user_email = None
        if access_token:
            try:
                user_response = supabase_client.auth.get_user(access_token)
                user_email = user_response.user.email if user_response.user else None
            except Exception as e:
                logger.warning(f"Failed to get user email: {e}")

        user = {
            "email": user_email,
            "full_name": profile.get("full_name"),
            "avatar_url": profile.get("avatar_url")
        }

        return templates.TemplateResponse(
            "shotlist/dashboard.html",
            {
                "request": request,
                "user": user,
                "projects": projects,
                "videos": videos,
                "selected_project_id": project_id
            }
        )
    except Exception as e:
        logger.error(f"Shotlist dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load shotlist dashboard")


@router.get("/shotlist/video/{video_id}", response_class=HTMLResponse)
async def video_detail(
    request: Request,
    video_id: str,
    user_id: str = Depends(require_auth())
):
    """
    Video detail page - Shot list editor.
    """
    try:
        # Get video details
        video = shotlist_service.get_video_by_id(user_id, video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        # Get shots for this video
        shots = shotlist_service.get_video_shots(video_id)

        # Get all projects for project selector
        projects = shotlist_service.get_user_projects(user_id)

        # Get user info
        from app.utils.session import get_access_token
        from app.services.supabase_client import supabase_client

        access_token = get_access_token(request)
        profile_response = supabase_client.table("profiles").select("*").eq("id", user_id).single().execute()
        profile = profile_response.data

        user_email = None
        if access_token:
            try:
                user_response = supabase_client.auth.get_user(access_token)
                user_email = user_response.user.email if user_response.user else None
            except Exception as e:
                logger.warning(f"Failed to get user email: {e}")

        user = {
            "email": user_email,
            "full_name": profile.get("full_name"),
            "avatar_url": profile.get("avatar_url")
        }

        return templates.TemplateResponse(
            "shotlist/video_detail.html",
            {
                "request": request,
                "user": user,
                "video": video,
                "shots": shots,
                "projects": projects
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video detail error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load video detail")


# ============================================
# PROJECT API ROUTES
# ============================================

@router.post("/api/shotlist/projects")
async def create_project(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    user_id: str = Depends(require_auth())
):
    """Create a new project."""
    try:
        project_data = ProductionProjectCreate(name=name, description=description)
        project = shotlist_service.create_project(user_id, project_data)
        return JSONResponse(content={"success": True, "project": project})
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail="Failed to create project")


@router.delete("/api/shotlist/projects/{project_id}")
async def delete_project(
    project_id: str,
    user_id: str = Depends(require_auth())
):
    """Delete a project."""
    try:
        shotlist_service.delete_project(user_id, project_id)
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Failed to delete project: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete project")


# ============================================
# VIDEO API ROUTES
# ============================================

@router.post("/api/shotlist/videos")
async def create_video(
    request: Request,
    title: str = Form(...),
    project_id: Optional[str] = Form(None),
    idea: Optional[str] = Form(None),
    user_id: str = Depends(require_auth())
):
    """Create a new video."""
    try:
        video_data = ProductionVideoCreate(
            title=title,
            project_id=project_id if project_id else None,
            idea=idea
        )
        video = shotlist_service.create_video(user_id, video_data)
        return JSONResponse(content={"success": True, "video": video})
    except Exception as e:
        logger.error(f"Failed to create video: {e}")
        raise HTTPException(status_code=500, detail="Failed to create video")


@router.put("/api/shotlist/videos/{video_id}")
async def update_video(
    video_id: str,
    field: str = Form(...),
    value: str = Form(...),
    user_id: str = Depends(require_auth())
):
    """Update a video field."""
    try:
        video = shotlist_service.update_video(user_id, video_id, field, value)
        return JSONResponse(content={"success": True, "video": video})
    except Exception as e:
        logger.error(f"Failed to update video: {e}")
        raise HTTPException(status_code=500, detail="Failed to update video")


@router.delete("/api/shotlist/videos/{video_id}")
async def delete_video(
    video_id: str,
    user_id: str = Depends(require_auth())
):
    """Delete a video."""
    try:
        shotlist_service.delete_video(user_id, video_id)
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Failed to delete video: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete video")


# ============================================
# SHOT API ROUTES
# ============================================

@router.post("/api/shotlist/shots")
async def create_shot(
    request: Request,
    video_id: str = Form(...),
    user_id: str = Depends(require_auth())
):
    """Create a new shot."""
    try:
        # Verify user owns this video
        video = shotlist_service.get_video_by_id(user_id, video_id)
        if not video:
            raise HTTPException(status_code=403, detail="Forbidden")

        # Get current shot count to set order_index
        shots = shotlist_service.get_video_shots(video_id)
        order_index = len(shots)

        shot_data = {
            "video_id": video_id,
            "order_index": order_index
        }
        shot = shotlist_service.create_shot(shot_data)

        # Return the shot row partial for HTMX
        return templates.TemplateResponse(
            "shotlist/partials/shot_row.html",
            {"request": request, "shot": shot, "video": video}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create shot: {e}")
        raise HTTPException(status_code=500, detail="Failed to create shot")


@router.put("/api/shotlist/shots/{shot_id}")
async def update_shot(
    shot_id: str,
    field: str = Form(...),
    value: str = Form(...),
    user_id: str = Depends(require_auth())
):
    """Update a shot field."""
    try:
        # Handle JSON fields (vibes, music_vibes)
        if field in ["vibes", "music_vibes"]:
            import json
            value = json.loads(value) if value else []

        shot = shotlist_service.update_shot(shot_id, field, value)
        return JSONResponse(content={"success": True, "shot": shot})
    except Exception as e:
        logger.error(f"Failed to update shot: {e}")
        raise HTTPException(status_code=500, detail="Failed to update shot")


@router.delete("/api/shotlist/shots/{shot_id}")
async def delete_shot(
    shot_id: str,
    user_id: str = Depends(require_auth())
):
    """Delete a shot."""
    try:
        shotlist_service.delete_shot(shot_id)
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Failed to delete shot: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete shot")


@router.post("/api/shotlist/shots/reorder")
async def reorder_shots(
    request: Request,
    user_id: str = Depends(require_auth())
):
    """Reorder shots."""
    try:
        data = await request.json()
        shot_ids = data.get("shot_ids", [])
        shotlist_service.reorder_shots(shot_ids)
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Failed to reorder shots: {e}")
        raise HTTPException(status_code=500, detail="Failed to reorder shots")
