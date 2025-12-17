import google.generativeai as genai
from typing import List
import logging
import json
import re

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AIService:
    """Service for AI-powered channel suggestions using Google Gemini with Claude fallback."""

    def __init__(self):
        """Initialize AI services with API keys."""
        # Initialize Gemini
        api_key = settings.gemini_api_key or settings.google_api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

        # Initialize Claude (optional fallback)
        self.claude_client = None
        if settings.anthropic_api_key:
            try:
                from anthropic import Anthropic
                self.claude_client = Anthropic(api_key=settings.anthropic_api_key)
                logger.info("✓ Claude API initialized as fallback")
            except ImportError:
                logger.warning("anthropic package not installed - Claude fallback unavailable")

    def get_channel_suggestions(self, persona: str, num_channels: int = 10) -> List[str]:
        """
        Generate YouTube channel suggestions based on target viewer persona.

        Args:
            persona: Description of target viewer (e.g., "25yo Junior Dev")
            num_channels: Number of channels to suggest (default: 10)

        Returns:
            List of channel handles (e.g., ["@ThePrimeagen", "@MrBeast"])
        """
        logger.info(f"Getting {num_channels} channel suggestions for persona: {persona[:50]}...")

        prompt = f"""
Based on this specific Target Viewer Persona, list exactly {num_channels} real, active, and specific YouTube channels they would watch regularly.

Target Viewer Persona: "{persona}"

IMPORTANT REQUIREMENTS:
1. Return ONLY the YouTube handles (e.g., @Veritasium, @MrBeast, @ThePrimeagen)
2. Each handle must be a real, existing YouTube channel
3. Channels should be highly relevant to this specific persona
4. Focus on popular, active channels with recent content
5. Output as a clean JSON array of strings

Example output format:
["@ChannelName1", "@ChannelName2", "@ChannelName3"]

Return ONLY the JSON array, no other text.
"""

        # Try Gemini first
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()

            channels = self._parse_channel_response(text, num_channels)

            if channels:
                logger.info(f"✓ Gemini: Generated {len(channels)} channel suggestions")
                return channels
            else:
                logger.warning("Gemini: Failed to parse response, trying Claude fallback")
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            logger.info("Trying Claude fallback...")

        # Try Claude as fallback
        if self.claude_client:
            try:
                channels = self._get_claude_suggestions(num_channels, prompt)
                if channels:
                    logger.info(f"✓ Claude: Generated {len(channels)} channel suggestions")
                    return channels
            except Exception as e:
                logger.error(f"Claude API error: {e}")

        # Last resort: hardcoded fallback
        logger.warning("All AI services failed, using hardcoded fallback")
        return self._fallback_channels(num_channels)

    def _get_claude_suggestions(self, num_channels: int, prompt: str) -> List[str]:
        """
        Get channel suggestions using Claude API.

        Args:
            num_channels: Number of channels to suggest
            prompt: The prompt to send to Claude

        Returns:
            List of channel handles
        """
        message = self.claude_client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        text = message.content[0].text.strip()
        return self._parse_channel_response(text, num_channels)

    def _parse_channel_response(self, text: str, expected_count: int) -> List[str]:
        """
        Parse channel suggestions from AI response.

        Tries multiple parsing strategies to extract channel handles.
        """
        # Strategy 1: Parse as JSON array
        try:
            # Clean up markdown code blocks if present
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'^```\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            text = text.strip()

            channels = json.loads(text)
            if isinstance(channels, list):
                # Clean and validate handles
                cleaned = []
                for ch in channels:
                    if isinstance(ch, str):
                        ch = ch.strip()
                        if not ch.startswith('@'):
                            ch = f"@{ch}"
                        cleaned.append(ch)

                return cleaned[:expected_count]
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract handles using regex
        handles = re.findall(r'@[\w-]+', text)
        if handles:
            return handles[:expected_count]

        # Strategy 3: Parse comma-separated list
        if ',' in text:
            parts = [p.strip() for p in text.split(',')]
            channels = []
            for part in parts:
                # Clean up quotes, brackets, etc.
                part = re.sub(r'["\[\]]', '', part).strip()
                if part and not part.startswith('{'):
                    if not part.startswith('@'):
                        part = f"@{part}"
                    channels.append(part)

            if channels:
                return channels[:expected_count]

        return []

    def _fallback_channels(self, num_channels: int) -> List[str]:
        """
        Fallback channel list in case AI fails.

        Returns popular, diverse channels as a safety net.
        """
        fallback = [
            "@MrBeast",
            "@Veritasium",
            "@ThePrimeagen",
            "@mkbhd",
            "@LinusTechTips",
            "@3Blue1Brown",
            "@vsauce",
            "@CGPGrey",
            "@TomScottGo",
            "@Fireship"
        ]

        logger.warning(f"Using fallback channel list (requested: {num_channels})")
        return fallback[:num_channels]
