from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
import logging
from typing import Optional, List

from app.services.creator_profile_service import CreatorProfileService
from app.utils.session import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/creator-profile", tags=["creator-profile"])

@router.post("")
async def create_or_update_profile(
    request: Request,
    creator_name: str = Form(...),
    niche: str = Form(...),
    bio: Optional[str] = Form(None),
    tone_preference: Optional[str] = Form(None),
    target_audience: Optional[str] = Form(None),
    expertise_areas: Optional[str] = Form(None),
    additional_notes: Optional[str] = Form(None)
):
    """
    Create or update the user's creator profile.
    """
    try:
        # Get authenticated user
        user = await get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user_id = user['user_id']
        
        # Parse expertise areas (comma separated)
        expertise_list = []
        if expertise_areas:
            expertise_list = [area.strip() for area in expertise_areas.split(',') if area.strip()]
            
        # Prepare profile data
        profile_data = {
            'creator_name': creator_name,
            'niche': niche,
            'bio': bio,
            'tone_preference': tone_preference,
            'target_audience': target_audience,
            'expertise_areas': expertise_list,
            'additional_notes': additional_notes
        }
        
        # Service instance
        service = CreatorProfileService()
        
        # Check if profile exists to determine update or create
        exists = service.profile_exists(user_id)
        
        if exists:
            result = service.update_profile(user_id, profile_data)
            action = "updated"
        else:
            result = service.create_profile(user_id, profile_data)
            action = "created"
            
        if result:
            return JSONResponse({
                'success': True,
                'message': f'Profile {action} successfully',
                'profile': result
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to save profile")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving creator profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))
