"""
Encryption utilities for secure data storage.

Uses Fernet symmetric encryption for API keys and other sensitive data.
"""

import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """
    Get Fernet instance using the app's secret key.

    Uses PBKDF2 to derive a proper 32-byte key from the Supabase secret key.
    """
    settings = get_settings()

    # Use Supabase secret key as the base for encryption
    # In production, you might want a dedicated ENCRYPTION_KEY env var
    secret = settings.supabase_secret_key.encode()

    # Derive a proper 32-byte key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"youtube_competitive_intel_salt",  # Static salt is fine for this use case
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret))

    return Fernet(key)


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for secure storage.

    Args:
        api_key: The plaintext API key

    Returns:
        Base64-encoded encrypted string
    """
    if not api_key:
        return ""

    try:
        fernet = _get_fernet()
        encrypted = fernet.encrypt(api_key.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Failed to encrypt API key: {e}")
        raise ValueError("Failed to encrypt API key")


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt an encrypted API key.

    Args:
        encrypted_key: Base64-encoded encrypted string

    Returns:
        The plaintext API key
    """
    if not encrypted_key:
        return ""

    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(encrypted_key.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt API key: {e}")
        raise ValueError("Failed to decrypt API key")
