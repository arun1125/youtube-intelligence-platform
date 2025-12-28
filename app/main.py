from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from app.core.config import get_settings
from app.features.thumbnail import router as thumbnail
from app.features.auth import router as auth
from app.features.dashboard import router as dashboard
from app.features.user import router as user
from app.features.payment import router as payment
from app.features.shotlist import router as shotlist
from app.features.viral_researcher import router as viral_researcher
from app.features.creator import router as creator_profile
from app.utils.helpers import format_duration, format_view_count, format_time_ago
from app.utils.session import get_session_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Register custom Jinja2 filters
templates.env.filters["format_duration"] = format_duration
templates.env.filters["format_view_count"] = format_view_count
templates.env.filters["format_time_ago"] = format_time_ago

# Attach templates to app state for access in routers
app.state.templates = templates

# Add CORS middleware
# In production, this will be restricted to your domain
allowed_origins = ["*"] if settings.debug else [
    "https://youtube-intelligence-platform.onrender.com",
    "http://localhost:8000",  # Keep for local testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(payment.router)
app.include_router(dashboard.router)
app.include_router(thumbnail.router)
app.include_router(shotlist.router)
app.include_router(viral_researcher.router)
app.include_router(creator_profile.router)

# Home page route
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page with feature cards."""
    from app.middleware.auth import optional_auth

    # Get user info if authenticated
    user_data = None
    try:
        session_data = get_session_data(request)
        if session_data:
            from app.core.database import supabase_client
            access_token = session_data.get("access_token")
            if access_token:
                user_response = supabase_client.auth.get_user(access_token)
                user_data = {
                    "email": user_response.user.email if user_response.user else None,
                    "full_name": None,
                    "avatar_url": None
                }
    except Exception:
        pass  # Not authenticated or error, just show public page

    return templates.TemplateResponse(
        "home.html",
        {"request": request, "user": user_data}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Run startup tasks."""
    logger.info(f"🚀 Starting {settings.app_name} v{settings.app_version}")

    # Ensure required directories exist
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.data_dir, exist_ok=True)

    logger.info(f"✓ Upload directory: {settings.upload_dir}")
    logger.info(f"✓ Data directory: {settings.data_dir}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info(f"👋 Shutting down {settings.app_name}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
