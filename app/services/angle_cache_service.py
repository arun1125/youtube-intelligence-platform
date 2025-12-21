from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class AngleCacheService:
    """
    Simple in-memory cache to store generated angles temporarily.
    This avoids the need for database schema changes for intermediate steps.
    """
    _instance = None
    _cache: Dict[str, List[Any]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AngleCacheService, cls).__new__(cls)
        return cls._instance

    def save_angles(self, video_id: str, angles: List[Any]):
        """Store angles for a video."""
        self._cache[video_id] = angles
        logger.info(f"Cached {len(angles)} angles for video {video_id}")

    def get_angles(self, video_id: str) -> List[Any]:
        """Retrieve angles for a video."""
        return self._cache.get(video_id, [])

    def get_angle_by_index(self, video_id: str, index: int) -> Any:
        """Retrieve a specific angle by index."""
        angles = self.get_angles(video_id)
        if 0 <= index < len(angles):
            return angles[index]
        return None
