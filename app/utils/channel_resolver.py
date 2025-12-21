import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


def get_channel_id_from_html(channel_input: str) -> Tuple[Optional[str], str]:
    """
    Scrape Channel ID (UC...) from Channel Page HTML.

    This is the mandatory function from spec.md Section 6.

    Args:
        channel_input: Channel handle or name (e.g., "@ThePrimeagen" or "ThePrimeagen")

    Returns:
        Tuple of (channel_id, url) where channel_id is None if not found
    """
    clean_input = channel_input.strip()

    # Case 1: Full URL
    if "youtube.com" in clean_input or "youtu.be" in clean_input:
        if "@" in clean_input and "channel/" not in clean_input and "c/" not in clean_input:
            # Extract handle from URL (e.g. https://youtube.com/@user)
            clean_input = clean_input.split("youtube.com/")[-1].split("?")[0]
            # Ensure it starts with @ (usually it does if split correctly)
            if not clean_input.startswith("@"):
                 clean_input = f"@{clean_input}"
        else:
             # It's a channel ID link or custom name, use as is
             url = clean_input
             logger.info(f"Resolving ID for URL: {url}")
             clean_input = None # Marker

    # Case 2: Handle or Name
    if clean_input:
        if not clean_input.startswith("@"):
            clean_input = f"@{clean_input}"
        url = f"https://www.youtube.com/{clean_input}"
        logger.info(f"Resolving ID for handle: {clean_input}")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            match = re.search(r'https://www\.youtube\.com/channel/(UC[\w-]{22})', response.text)
            if match:
                return match.group(1), url

            # Fallback: Look for "externalId":"UC..." pattern in JSON blobs in HTML
            match_json = re.search(r'"externalId":"(UC[\w-]{22})"', response.text)
            if match_json:
                return match_json.group(1), url

        return None, url
    except Exception as e:
        logger.error(f"Request Error for {clean_input}: {e}")
        return None, url


def resolve_channel_handle(channel_handle: str) -> Optional[dict]:
    """
    Resolve a single channel handle to channel ID.

    Returns:
        Dict with channel_id, handle, and success status
    """
    channel_id, url = get_channel_id_from_html(channel_handle)

    return {
        'handle': channel_handle,
        'channel_id': channel_id,
        'url': url,
        'success': channel_id is not None
    }


def resolve_channels_parallel(channel_handles: List[str], max_workers: int = 10) -> List[dict]:
    """
    Resolve multiple channel handles to channel IDs in parallel using ThreadPoolExecutor.

    Args:
        channel_handles: List of channel handles (e.g., ["@ThePrimeagen", "@MrBeast"])
        max_workers: Maximum number of parallel threads

    Returns:
        List of dicts containing channel resolution results
    """
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_handle = {
            executor.submit(resolve_channel_handle, handle): handle
            for handle in channel_handles
        }

        # Collect results as they complete
        for future in as_completed(future_to_handle):
            handle = future_to_handle[future]
            try:
                result = future.result()
                results.append(result)
                if result['success']:
                    logger.info(f"✓ Resolved {handle} -> {result['channel_id']}")
                else:
                    logger.warning(f"✗ Failed to resolve {handle}")
            except Exception as e:
                logger.error(f"Exception resolving {handle}: {e}")
                results.append({
                    'handle': handle,
                    'channel_id': None,
                    'url': None,
                    'success': False
                })

    return results
