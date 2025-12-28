"""
Angle Generator Service

Uses Claude to generate creative re-angles for viral videos based on user's creator profile.
"""
from typing import List, Dict
import logging
import json

from anthropic import Anthropic

from app.core.config import get_settings

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
        # Extract key topic from title for context
        title = video_data.get('title', '')

        prompt = f"""You are a viral video strategist who specializes in finding unique, compelling angles that haven't been done before.

## THE VIRAL VIDEO YOU'RE ANALYZING:

**Title:** {title}
**Performance:** {video_data.get('view_count', 0):,} views
**Duration:** {video_data.get('duration_seconds', 0)} seconds

**What the video actually covers:**
{transcript_summary}

---

## THE CREATOR WHO WANTS TO MAKE THEIR VERSION:

**Creator:** {profile.get('creator_name', 'Independent Creator')}
**Their Niche:** {profile.get('niche', 'General')}
**Expertise Areas:** {', '.join(profile.get('expertise_areas', ['General knowledge']))}
**Their Style/Tone:** {profile.get('tone_preference', 'Informative')}
**Target Audience:** {profile.get('target_audience', 'General viewers')}
**About Them:** {profile.get('bio', 'A content creator looking to grow their channel')}

---

## YOUR MISSION:

Generate 4 UNIQUE angles this creator could use to make their own video on this topic.

### CRITICAL RULES - READ CAREFULLY:

1. **NO GENERIC TEMPLATES** - Do NOT suggest things like:
   - "Deep Dive Analysis"
   - "Beginner's Guide"
   - "Contrarian Take"
   - "Case Study"
   - "Behind the Scenes"
   These are lazy and overdone.

2. **SPECIFICITY IS EVERYTHING** - Each angle must reference:
   - Specific concepts, names, or ideas from the transcript
   - The creator's specific expertise
   - A unique perspective nobody else would think of

3. **THE HOOK MUST STOP THE SCROLL** - Write hooks that:
   - Create an "open loop" (unanswered question)
   - Challenge a common belief
   - Promise insider knowledge
   - Use specific numbers or claims

4. **THINK LIKE A STRATEGIST** - Consider:
   - What angle would get THIS creator's audience excited?
   - What's the creator uniquely positioned to discuss?
   - What hasn't been said about this topic yet?

---

## ANGLE CATEGORIES TO CONSIDER (pick the best 4):

- **The Insider Angle**: What does this creator know that others don't?
- **The Prediction Angle**: What will happen next? What are the implications?
- **The Connection Angle**: How does this connect to something unexpected?
- **The Personal Stake Angle**: Why does this matter to the creator personally?
- **The Mythbusting Angle**: What does everyone get wrong about this?
- **The "What If" Angle**: Explore an alternative scenario
- **The Historical Angle**: How does this compare to similar past events?
- **The Practical Angle**: How can viewers actually use this information?

---

## OUTPUT FORMAT:

Return ONLY a valid JSON array. No markdown, no explanations.

Each angle object must have:
- "angle_name": A catchy, SPECIFIC name (NOT generic like "Deep Dive")
- "core_hook": The opening line that makes viewers click (specific, intriguing)
- "key_differentiator": Why this angle is different from the original AND from other creators
- "target_emotion": One of: curiosity, outrage, hope, fear, excitement, validation
- "estimated_appeal": "high" or "medium" based on fit with creator's audience
- "why_this_works": One sentence explaining why this angle will perform

Example of a GOOD angle (do NOT copy this, create your own based on the actual video):
{{
  "angle_name": "The $50M Mistake Everyone's Ignoring",
  "core_hook": "Everyone's celebrating this launch, but I found a clause in the terms of service that could bankrupt early adopters",
  "key_differentiator": "While others cover the hype, I'm examining the legal fine print with my background in tech law",
  "target_emotion": "fear",
  "estimated_appeal": "high",
  "why_this_works": "Contrarian angles with specific stakes always outperform positive coverage"
}}

Now generate 4 angles for the video above, tailored to this specific creator:
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
            - why_this_works
        """
        try:
            # Use first 1500 words for better context (roughly 3-4 minutes of content)
            words = transcript.split()[:1500]
            transcript_summary = ' '.join(words)

            # If transcript is short, use it all
            if len(transcript.split()) <= 1500:
                transcript_summary = transcript

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
                return self._get_fallback_angles(video_data, profile)

        except Exception as e:
            logger.error(f"Error generating angles: {e}")
            return self._get_fallback_angles(video_data, profile)

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

    def _get_fallback_angles(self, video_data: Dict = None, profile: Dict = None) -> List[Dict]:
        """
        Get fallback angles if Claude fails.

        These are still useful angles but less tailored than AI-generated ones.

        Args:
            video_data: Optional video data to personalize fallbacks
            profile: Optional creator profile

        Returns:
            List of angle dicts
        """
        logger.warning("Using fallback angles - Claude generation failed")

        title = video_data.get('title', 'this topic') if video_data else 'this topic'
        niche = profile.get('niche', 'your niche') if profile else 'your niche'
        expertise = profile.get('expertise_areas', ['your expertise'])[0] if profile else 'your expertise'

        return [
            {
                "angle_name": f"The {niche} Perspective",
                "core_hook": f"As someone who's spent years in {niche}, here's what everyone else is missing about '{title}'",
                "key_differentiator": f"Bringing {expertise} expertise to a topic that's usually covered by generalists",
                "target_emotion": "curiosity",
                "estimated_appeal": "high",
                "why_this_works": "Your unique expertise adds credibility and fresh insights"
            },
            {
                "angle_name": "The 3 Things Nobody Mentions",
                "core_hook": f"I watched 20 videos about this topic. Here are the 3 critical things they all got wrong",
                "key_differentiator": "Meta-analysis approach that positions you as the definitive source",
                "target_emotion": "curiosity",
                "estimated_appeal": "high",
                "why_this_works": "Number-based hooks with contrarian framing perform well"
            },
            {
                "angle_name": "The Real-World Test",
                "core_hook": f"I actually tried this for 30 days. Here's what happened (with receipts)",
                "key_differentiator": "First-hand experience and proof instead of just commentary",
                "target_emotion": "validation",
                "estimated_appeal": "high",
                "why_this_works": "Personal experiments with documented results build trust"
            },
            {
                "angle_name": "The Future Implications",
                "core_hook": f"Everyone's focused on today. But in 2 years, this changes everything about {niche}",
                "key_differentiator": "Forward-looking analysis that makes viewers feel ahead of the curve",
                "target_emotion": "fear",
                "estimated_appeal": "medium",
                "why_this_works": "Prediction content creates urgency and shareability"
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
        result = f"""**{angle.get('angle_name')}**

Hook: {angle.get('core_hook')}

Differentiator: {angle.get('key_differentiator')}

Target Emotion: {angle.get('target_emotion', 'N/A')}
Appeal: {angle.get('estimated_appeal', 'N/A')}"""

        # Add why_this_works if present
        if angle.get('why_this_works'):
            result += f"\nWhy It Works: {angle.get('why_this_works')}"

        return result
