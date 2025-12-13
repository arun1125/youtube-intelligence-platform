from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from app.config import get_settings
from app.routes import thumbnail, auth, dashboard, user, payment
from app.utils.helpers import format_duration, format_view_count, format_time_ago

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
