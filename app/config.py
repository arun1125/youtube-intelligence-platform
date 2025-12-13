from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings and configuration."""

    # App Info
    app_name: str = "YouTube Context Engine"
    app_version: str = "1.0.0"
    debug: bool = True

    # Supabase
    supabase_url: str
    supabase_publishable_key: str
    supabase_secret_key: str

    # Google API Keys
    google_api_key: str
    gemini_api_key: str = ""  # Optional if using same key

    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str

    # Stripe
    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_price_id_pro: str
    stripe_webhook_secret: str = ""  # Optional for local dev

    # Gemini Configuration
    gemini_model: str = "gemini-2.0-flash-exp"  # Higher free tier quota than preview models

    # File Storage
    upload_dir: str = "static/uploads"
    data_dir: str = "data"
    csv_file: str = "data/competitor_data.csv"

    # Processing Settings
    max_channels: int = 10
    videos_per_channel: int = 2  # Reduced for better even distribution (10 channels x 2 = 20 videos)
    max_workers: int = 10  # For parallel channel resolution
    request_timeout: int = 10

    # Shorts Filter
    shorts_duration_threshold: int = 60  # seconds

    # Server Configuration
    host: str = "127.0.0.1"
    port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields in .env file


@lru_cache()
def get_settings() -> Settings:
    """Cache settings instance."""
    return Settings()
