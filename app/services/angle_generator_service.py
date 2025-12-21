"""
Angle Generator Service

Uses Claude to generate creative re-angles for viral videos based on user's creator profile.
"""
from typing import List, Dict
import logging
import json

from anthropic import Anthropic

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AngleGeneratorService:
    """Service for generating creative angles using Claude."""

    def __init__(self):
        """Initialize the angle generator service."""
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model

    def _build_angle_prompt(self, video_data: Dict, profile: Dict, transcript_summary: str) -> str:
        """
        Build the prompt for Claude to generate angles.

        Args:
            video_data: Dict with video details (title, views, etc.)
            profile: User creator profile
            transcript_summary: Summary of the video transcript

        Returns:
            Formatted prompt string
        """
        prompt = f"""Analyze this viral video and generate 3-5 alternative angles for creating a similar video tailored to this creator's profile.

**Original Video:**
- Title: {video_data.get('title')}
- Views: {video_data.get('view_count'):,}
- Duration: {video_data.get('duration_seconds')} seconds
- Transcript Summary (first 500 words):
{transcript_summary}

**Creator Profile:**
- Name: {profile.get('creator_name', 'Not specified')}
- Niche: {profile.get('niche', 'Not specified')}
- Expertise: {', '.join(profile.get('expertise_areas', []))}
- Tone: {profile.get('tone_preference', 'Not specified')}
- Target Audience: {profile.get('target_audience', 'Not specified')}
- Bio: {profile.get('bio', 'Not specified')}

**Your Task:**
Generate 3-5 alternative angles for this creator to make a similar video. Each angle should:
1. Leverage the creator's expertise and niche
2. Match their tone and target audience
3. Differentiate from the original video
4. Create curiosity and engagement

**For each angle, provide:**
1. **Angle Name** (e.g., "Technical Deep Dive", "Contrarian Take", "Beginner-Friendly Version")
2. **Core Hook** (one compelling sentence that grabs attention)
3. **Key Differentiator** (what makes this angle unique from the original)
4. **Target Emotion** (curiosity, controversy, inspiration, education, entertainment)
5. **Estimated Appeal** (high/medium for this creator's audience)

**Output Format:**
Return ONLY a valid JSON array with 3-5 angle objects. No other text.

Example format:
[
  {{
    "angle_name": "Technical Deep Dive",
    "core_hook": "Everyone talks about the results, but nobody explains the engineering behind it",
    "key_differentiator": "Focus on technical implementation details that creators skip",
    "target_emotion": "curiosity",
    "estimated_appeal": "high"
  }},
  ...
]
"""
        return prompt

    def generate_angles(self, video_data: Dict, profile: Dict, transcript: str) -> List[Dict]:
        """
        Generate 3-5 creative angles for a video.

        Args:
            video_data: Dict with video details
            profile: User creator profile
            transcript: Full video transcript

        Returns:
            List of angle dicts with keys:
            - angle_name
            - core_hook
            - key_differentiator
            - target_emotion
            - estimated_appeal
        """
        try:
            # Truncate transcript to first 500 words for summary
            words = transcript.split()[:500]
            transcript_summary = ' '.join(words)

            # Build prompt
            prompt = self._build_angle_prompt(video_data, profile, transcript_summary)

            logger.info(f"Generating angles for video: {video_data.get('title')}")

            # Call Claude
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extract response
            response_text = message.content[0].text.strip()

            # Parse JSON
            angles = self._parse_angles_response(response_text)

            if angles:
                logger.info(f"✓ Generated {len(angles)} angles")
                return angles
            else:
                logger.error("Failed to parse angles from Claude response")
                return self._get_fallback_angles()

        except Exception as e:
            logger.error(f"Error generating angles: {e}")
            return self._get_fallback_angles()

    def _parse_angles_response(self, response_text: str) -> List[Dict]:
        """
        Parse JSON response from Claude.

        Args:
            response_text: Claude's response

        Returns:
            List of angle dicts
        """
        try:
            # Remove markdown code blocks if present
            response_text = response_text.replace('```json', '').replace('```', '').strip()

            # Parse JSON
            angles = json.loads(response_text)

            # Validate structure
            if isinstance(angles, list) and len(angles) >= 3:
                # Ensure each angle has required fields
                valid_angles = []
                for angle in angles:
                    if all(k in angle for k in ['angle_name', 'core_hook', 'key_differentiator']):
                        valid_angles.append(angle)

                return valid_angles[:5]  # Max 5 angles

            return []

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing angles: {e}")
            return []

    def _get_fallback_angles(self) -> List[Dict]:
        """
        Get fallback angles if Claude fails.

        Returns:
            List of generic angle dicts
        """
        logger.warning("Using fallback angles")
        return [
            {
                "angle_name": "Deep Dive Analysis",
                "core_hook": "Let's break down what really made this work",
                "key_differentiator": "Technical analysis with actionable insights",
                "target_emotion": "curiosity",
                "estimated_appeal": "medium"
            },
            {
                "angle_name": "Beginner-Friendly Version",
                "core_hook": "Here's everything you need to know as a complete beginner",
                "key_differentiator": "Simplified for newcomers with step-by-step guidance",
                "target_emotion": "education",
                "estimated_appeal": "high"
            },
            {
                "angle_name": "Contrarian Perspective",
                "core_hook": "Everyone's excited about this, but here's what they're missing",
                "key_differentiator": "Critical analysis highlighting overlooked issues",
                "target_emotion": "controversy",
                "estimated_appeal": "medium"
            }
        ]

    def format_angle_for_display(self, angle: Dict) -> str:
        """
        Format an angle for display in UI.

        Args:
            angle: Angle dict

        Returns:
            Formatted string
        """
        return f"""**{angle.get('angle_name')}**

Hook: {angle.get('core_hook')}

Differentiator: {angle.get('key_differentiator')}

Target Emotion: {angle.get('target_emotion', 'N/A')}
Appeal: {angle.get('estimated_appeal', 'N/A')}
"""
