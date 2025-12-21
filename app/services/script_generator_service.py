"""
Script Generator Service

Uses Claude to generate high-retention scripts based on research brief and creator profile.
Includes knowledge base from viral video transcripts.
"""
from typing import Dict, List
import logging
import json
import pickle
import os

from anthropic import Anthropic

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ScriptGeneratorService:
    """Service for generating scripts using Claude with research and knowledge base."""

    def __init__(self):
        """Initialize the script generator service."""
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.knowledge_base = self._load_knowledge_base()

    def _load_knowledge_base(self) -> Dict[str, str]:
        """
        Load knowledge base from pickle file (viral video transcripts).

        Returns:
            Dict mapping video titles to transcripts
        """
        try:
            kb_path = os.path.join(settings.data_dir, 'kb_full.pkl')

            # Check if file exists
            if not os.path.exists(kb_path):
                logger.warning(f"Knowledge base not found at {kb_path}")
                return {}

            with open(kb_path, 'rb') as f:
                kb = pickle.load(f)

            logger.info(f"✓ Loaded knowledge base with {len(kb)} video transcripts")
            return kb

        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
            return {}

    def _build_script_prompt(
        self,
        video_data: Dict,
        selected_angle: Dict,
        research_brief: Dict,
        profile: Dict
    ) -> str:
        """
        Build the prompt for Claude to generate the script.

        Args:
            video_data: Original video details and transcript
            selected_angle: The angle user selected
            research_brief: Synthesized research from Gemini
            profile: Creator profile

        Returns:
            Formatted prompt string
        """
        # Format knowledge base examples
        kb_examples = ""
        if self.knowledge_base:
            kb_examples = "\n\n**Knowledge Base (Proven YouTube Success Patterns):**\n"
            kb_examples += "Here are transcripts from viral videos about making successful YouTube content. "
            kb_examples += "Use these as examples of proven hooks, structures, and retention techniques:\n\n"

            for i, (title, transcript) in enumerate(list(self.knowledge_base.items())[:3], 1):
                # Get first 1000 chars of each transcript
                kb_examples += f"{i}. \"{title}\"\n   {transcript[:1000]}...\n\n"

        # Format research brief
        new_facts_str = ""
        for fact in research_brief.get('new_facts', [])[:8]:
            new_facts_str += f"- {fact.get('fact')} (Source: {fact.get('source')})\n"

        narrative_hooks_str = "\n".join([f"- {hook}" for hook in research_brief.get('narrative_hooks', [])])

        # Get transcript summary
        transcript = video_data.get('transcript', '')
        transcript_words = transcript.split()[:300]
        transcript_summary = ' '.join(transcript_words)

        prompt = f"""Create a high-retention YouTube script using this research brief and angle.

**Original Video Context:**
- Title: {video_data.get('title')}
- Views: {video_data.get('view_count'):,}
- Main Points (first 300 words):
{transcript_summary}

**Selected Angle:**
- Name: {selected_angle.get('angle_name')}
- Hook: {selected_angle.get('core_hook')}
- Differentiator: {selected_angle.get('key_differentiator')}
- Target Emotion: {selected_angle.get('target_emotion')}

**Research Brief (Pre-Synthesized):**

Executive Summary:
{research_brief.get('executive_summary', 'N/A')}

New Facts to Incorporate:
{new_facts_str}

Suggested Narrative Hooks:
{narrative_hooks_str}

Key Statistics: {len(research_brief.get('key_statistics', []))} stats available
Compelling Quotes: {len(research_brief.get('compelling_quotes', []))} quotes available
Supporting Evidence: {len(research_brief.get('supporting_evidence', []))} evidence points available

**Creator Profile:**
- Name: {profile.get('creator_name', 'Creator')}
- Niche: {profile.get('niche', 'General')}
- Tone: {profile.get('tone_preference', 'Informative')}
- Target Audience: {profile.get('target_audience', 'General audience')}
- Expertise: {', '.join(profile.get('expertise_areas', []))}

{kb_examples}

**Your Task:**
Write a complete YouTube script that:

1. **Hook** (0-5 seconds): Use one of the suggested narrative hooks or the most compelling fact
2. **Introduction** (5-30 seconds): Set up the angle and value promise
3. **Main Content** (7-10 minutes):
   - Incorporate ALL new facts from the research brief naturally
   - Cite sources when mentioning data/stats
   - Use storytelling and examples
   - Match the creator's tone and expertise level
   - Include pattern interrupts every 60-90 seconds
4. **Conclusion & CTA** (30-60 seconds): Strong recap and call to action

**Style Guidelines:**
- Length: 8-12 minutes (approximately 1800-2200 words)
- Tone: {profile.get('tone_preference', 'Informative')}
- Audience: {profile.get('target_audience', 'General')}
- Use conversational language with "you" and "I"
- Include rhetorical questions to maintain engagement
- Add verbal cues for B-roll (e.g., "As you can see here...")

**Also Generate:**
1. Four high-CTR title variations (use power words specific to {profile.get('niche', 'this niche')})
2. Four thumbnail description variations (visual concepts that create curiosity)

**Output Format:**
Return ONLY valid JSON with this structure:

{{
  "script": "The complete script with [HOOK], [INTRO], [BODY], [CONCLUSION] markers",
  "titles": [
    "Title option 1",
    "Title option 2",
    "Title option 3",
    "Title option 4"
  ],
  "thumbnails": [
    "Thumbnail concept 1 description",
    "Thumbnail concept 2 description",
    "Thumbnail concept 3 description",
    "Thumbnail concept 4 description"
  ]
}}
"""
        return prompt

    def generate_script(
        self,
        video_data: Dict,
        selected_angle: Dict,
        research_brief: Dict,
        profile: Dict
    ) -> Dict:
        """
        Generate a complete YouTube script with titles and thumbnails.

        Args:
            video_data: Original video details and transcript
            selected_angle: The angle user selected
            research_brief: Synthesized research from Gemini
            profile: Creator profile

        Returns:
            Dict with:
            - script: Full script text
            - titles: List of 4 title options
            - thumbnails: List of 4 thumbnail descriptions
        """
        try:
            logger.info(f"Generating script for angle: {selected_angle.get('angle_name')}")

            # Build prompt
            prompt = self._build_script_prompt(
                video_data,
                selected_angle,
                research_brief,
                profile
            )

            # Call Claude
            message = self.client.messages.create(
                model=self.model,
                max_tokens=8192,  # Longer scripts need more tokens
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extract response
            response_text = message.content[0].text.strip()

            # Parse JSON
            result = self._parse_script_response(response_text)

            if result:
                logger.info(f"✓ Generated script ({len(result.get('script', ''))} chars)")
                return result
            else:
                logger.error("Failed to parse script from Claude response")
                return self._get_fallback_script(video_data, selected_angle)

        except Exception as e:
            logger.error(f"Error generating script: {e}")
            return self._get_fallback_script(video_data, selected_angle)

    def _parse_script_response(self, response_text: str) -> Dict:
        """
        Parse JSON response from Claude.

        Args:
            response_text: Claude's response

        Returns:
            Parsed script dict
        """
        try:
            # Remove markdown code blocks if present
            response_text = response_text.replace('```json', '').replace('```', '').strip()

            # Parse JSON
            result = json.loads(response_text)

            # Validate structure
            if 'script' in result and 'titles' in result and 'thumbnails' in result:
                return result

            logger.warning("Response missing required keys")
            return {}

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing script: {e}")
            return {}

    def _get_fallback_script(self, video_data: Dict, selected_angle: Dict) -> Dict:
        """
        Get a minimal fallback script if Claude fails.

        Args:
            video_data: Original video details
            selected_angle: The angle user selected

        Returns:
            Basic script dict
        """
        logger.warning("Using fallback script")

        script = f"""[HOOK]
{selected_angle.get('core_hook')}

[INTRO]
In this video, we're taking a fresh look at {video_data.get('title')} from a different angle.
{selected_angle.get('key_differentiator')}

[BODY]
Based on the research, here are the key points to cover:
- [Point 1 from research]
- [Point 2 from research]
- [Point 3 from research]

[CONCLUSION]
So there you have it. If you found this valuable, make sure to like and subscribe for more content like this.
"""

        return {
            'script': script,
            'titles': [
                f"The Truth About {video_data.get('title', 'This Topic')}",
                f"What They Don't Tell You About {video_data.get('title', 'This')}",
                f"I Analyzed {video_data.get('title', 'This')} - Here's What I Found",
                f"{selected_angle.get('angle_name')}: Deep Dive"
            ],
            'thumbnails': [
                "Large text: 'THE TRUTH' with surprised face expression",
                "Before/After comparison split screen",
                "Creator pointing at screen with key stat highlighted",
                "Contrarian viewpoint with crossed arms, serious expression"
            ]
        }

    def format_script_for_display(self, script: str) -> str:
        """
        Format script for display with section markers.

        Args:
            script: Raw script text

        Returns:
            Formatted script with clear sections
        """
        # Add visual separators
        script = script.replace('[HOOK]', '\n━━━━━━━━━━━━━━━━━\n📌 HOOK (0-5 seconds)\n━━━━━━━━━━━━━━━━━\n')
        script = script.replace('[INTRO]', '\n━━━━━━━━━━━━━━━━━\n🎬 INTRODUCTION (5-30 seconds)\n━━━━━━━━━━━━━━━━━\n')
        script = script.replace('[BODY]', '\n━━━━━━━━━━━━━━━━━\n📝 MAIN CONTENT (7-10 minutes)\n━━━━━━━━━━━━━━━━━\n')
        script = script.replace('[CONCLUSION]', '\n━━━━━━━━━━━━━━━━━\n🎯 CONCLUSION & CTA (30-60 seconds)\n━━━━━━━━━━━━━━━━━\n')

        return script
