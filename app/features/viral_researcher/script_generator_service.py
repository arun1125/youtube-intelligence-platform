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

from app.core.config import get_settings

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
            kb_examples += "Study these viral transcripts for hooks, pacing, and retention techniques:\n\n"

            for i, (title, transcript) in enumerate(list(self.knowledge_base.items())[:3], 1):
                kb_examples += f"{i}. \"{title}\"\n   {transcript[:1000]}...\n\n"

        # Format research brief - include all available data
        new_facts_str = ""
        for fact in research_brief.get('new_facts', [])[:8]:
            new_facts_str += f"- {fact.get('fact')} (Source: {fact.get('source')})\n"

        narrative_hooks_str = "\n".join([f"- {hook}" for hook in research_brief.get('narrative_hooks', [])])

        # Get key statistics
        stats_str = ""
        for stat in research_brief.get('key_statistics', [])[:5]:
            if isinstance(stat, dict):
                stats_str += f"- {stat.get('stat', stat)} (Source: {stat.get('source', 'Research')})\n"
            else:
                stats_str += f"- {stat}\n"

        # Get compelling quotes
        quotes_str = ""
        for quote in research_brief.get('compelling_quotes', [])[:3]:
            if isinstance(quote, dict):
                quotes_str += f"- \"{quote.get('quote', quote)}\" - {quote.get('source', 'Expert')}\n"
            else:
                quotes_str += f"- \"{quote}\"\n"

        # Get transcript summary
        transcript = video_data.get('transcript', '')
        transcript_words = transcript.split()[:400]
        transcript_summary = ' '.join(transcript_words)

        # Build creator personality guidelines
        tone = profile.get('tone_preference', 'Informative')
        tone_guidelines = self._get_tone_guidelines(tone)

        prompt = f"""You are a world-class YouTube scriptwriter who has written scripts for channels with 10M+ subscribers. Your scripts consistently achieve 70%+ average view duration.

Write a READY-TO-FILM script that requires ZERO editing. This should be exactly what the creator reads from the teleprompter.

═══════════════════════════════════════════════════════════════
CONTEXT & RESEARCH
═══════════════════════════════════════════════════════════════

**Original Video Being Reimagined:**
- Title: {video_data.get('title')}
- Views: {video_data.get('view_count'):,}
- Key Content:
{transcript_summary}

**Your Unique Angle:**
- Angle: {selected_angle.get('angle_name')}
- Core Hook: {selected_angle.get('core_hook')}
- What Makes This Different: {selected_angle.get('key_differentiator')}
- Target Emotion: {selected_angle.get('target_emotion')}

**Research Brief:**
Executive Summary: {research_brief.get('executive_summary', 'N/A')}

New Facts to Weave In:
{new_facts_str if new_facts_str else '- Use the angle and original video insights'}

Key Statistics:
{stats_str if stats_str else '- No specific stats provided'}

Expert Quotes:
{quotes_str if quotes_str else '- No specific quotes provided'}

Narrative Hook Options:
{narrative_hooks_str if narrative_hooks_str else '- Create a compelling hook based on the angle'}

**Creator Profile:**
- Name: {profile.get('creator_name', 'Creator')}
- Niche: {profile.get('niche', 'General')}
- Tone: {tone}
- Target Audience: {profile.get('target_audience', 'General audience')}
- Expertise Areas: {', '.join(profile.get('expertise_areas', [])) or 'General knowledge'}

{kb_examples}

═══════════════════════════════════════════════════════════════
SCRIPT REQUIREMENTS
═══════════════════════════════════════════════════════════════

**STRUCTURE (with timestamps):**

[HOOK] - First 5-8 seconds
- Open with a pattern interrupt: shocking stat, bold claim, or intriguing question
- NO greetings, NO "hey guys", NO channel name
- Create an "open loop" that MUST be resolved
- Example patterns: "What if I told you...", "Nobody's talking about...", "I just discovered..."

[INTRO] - 8-30 seconds
- Establish credibility WITHOUT bragging
- Preview the VALUE they'll get (be specific)
- Create stakes: why should they care RIGHT NOW?
- Transition naturally into the content

[SECTION 1] - ~2-3 minutes
- Lead with the most surprising insight
- Include: [B-ROLL: description of what to show]
- End with a mini-cliffhanger or tease of what's next

[PATTERN INTERRUPT 1]
- Quick aside, relatable observation, or "but here's the thing..."
- Re-engage viewers who might be drifting

[SECTION 2] - ~2-3 minutes
- Build on Section 1, go deeper
- Include at least one specific example or story
- Add [B-ROLL: description] markers
- Include a stat or quote for credibility

[PATTERN INTERRUPT 2]
- Different type than PI 1 (question, callback, or stakes reminder)

[SECTION 3] - ~2-3 minutes
- The "aha moment" - biggest insight or transformation
- This is where you deliver the core promise
- Include [B-ROLL: description] markers

[CONCLUSION] - 30-60 seconds
- Recap the key takeaway in ONE sentence
- Give a specific ACTIONABLE next step
- CTA: Natural, not begging ("If this changed how you think about X, you'll love my video on Y")
- End with a thought-provoking final line, not "bye!"

**FORMATTING FOR TELEPROMPTER:**
- Short sentences (max 15 words)
- One thought per line
- Use "..." for natural pauses
- Use CAPS for emphasis words
- Break after every complete thought
- Include [PAUSE] for dramatic effect
- Include [GESTURE: point, lean in, etc.] for physical cues

**B-ROLL MARKERS:**
Every 30-45 seconds, include:
[B-ROLL: specific description of footage to show]
Examples:
- [B-ROLL: Screen recording of the process]
- [B-ROLL: Stock footage of people doing X]
- [B-ROLL: Animated text showing "Key Point Here"]
- [B-ROLL: Cut to relevant clip/example]

**TONE & PERSONALITY:**
{tone_guidelines}

Match the creator's voice: {profile.get('creator_name', 'Creator')} speaks to {profile.get('target_audience', 'their audience')} about {profile.get('niche', 'their niche')}.

**RETENTION TECHNIQUES TO USE:**
1. Open loops (promise something, deliver later)
2. Specific numbers over vague claims
3. "The reason is..." before explanations
4. Mini-stories with characters and conflict
5. Callbacks to earlier points
6. Direct address: "You might be thinking..."
7. Contrarian takes backed by evidence
8. Bucket brigades: "Here's the thing:", "But wait:", "Now:"

═══════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════

Return ONLY valid JSON with this exact structure:

{{
  "script": "The COMPLETE script with all markers ([HOOK], [INTRO], [SECTION 1], [PATTERN INTERRUPT 1], [SECTION 2], [PATTERN INTERRUPT 2], [SECTION 3], [CONCLUSION]) and B-ROLL cues. Format for teleprompter with short lines.",
  "hook_options": [
    "Alternative hook 1 - different approach",
    "Alternative hook 2 - different approach",
    "Alternative hook 3 - different approach"
  ],
  "titles": [
    "Title 1 - curiosity gap style",
    "Title 2 - number/listicle style",
    "Title 3 - contrarian/unexpected style",
    "Title 4 - direct benefit style"
  ],
  "thumbnails": [
    "Thumbnail 1: [Emotion] + [Visual Element] + [Text Overlay]",
    "Thumbnail 2: [Emotion] + [Visual Element] + [Text Overlay]",
    "Thumbnail 3: [Emotion] + [Visual Element] + [Text Overlay]",
    "Thumbnail 4: [Emotion] + [Visual Element] + [Text Overlay]"
  ],
  "estimated_duration": "X minutes",
  "word_count": 0
}}

CRITICAL: The script must be 1800-2400 words, ready to read verbatim. Include ALL markers and B-roll cues inline.
"""
        return prompt

    def _get_tone_guidelines(self, tone: str) -> str:
        """Get specific writing guidelines based on tone preference."""
        tone_map = {
            "Informative": """
- Professional but accessible
- Use analogies to explain complex topics
- Cite sources naturally: "According to..."
- Confident but not arrogant
- Education-focused with practical takeaways""",

            "Casual": """
- Like talking to a friend
- Use contractions and casual phrases
- Self-deprecating humor welcome
- Tangents are okay if they add value
- End thoughts with relatable observations""",

            "Enthusiastic": """
- High energy throughout
- Use exclamation points sparingly but effectively
- Show genuine excitement about discoveries
- "This is INSANE" moments are encouraged
- Fast-paced transitions""",

            "Analytical": """
- Data-driven approach
- Break down complex topics step-by-step
- Use frameworks and mental models
- "Let me show you why..." structure
- Evidence before conclusions""",

            "Storytelling": """
- Lead with narrative
- Characters, conflict, resolution
- "Let me tell you about..."
- Emotional beats throughout
- Lessons emerge from stories""",

            "Provocative": """
- Challenge conventional wisdom
- Strong opinions backed by evidence
- "Here's what everyone gets wrong..."
- Create healthy tension
- Bold claims, then prove them"""
        }
        return tone_map.get(tone, tone_map["Informative"])

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

            # Validate structure - require core fields
            if 'script' in result and 'titles' in result and 'thumbnails' in result:
                # Ensure optional fields have defaults
                result.setdefault('hook_options', [])
                result.setdefault('estimated_duration', 'Unknown')
                result.setdefault('word_count', len(result.get('script', '').split()))
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
I've been researching this topic for weeks...
And what I found completely changed how I think about it.

[B-ROLL: Show research notes or computer screen]

In this video, we're taking a fresh look at {video_data.get('title')} from a different angle.
{selected_angle.get('key_differentiator')}

[SECTION 1]
Let's start with the most surprising discovery...

[B-ROLL: Relevant imagery for topic]

- Key insight 1 from the research
- Supporting evidence

[PATTERN INTERRUPT 1]
Now, you might be thinking...
"Okay, but how does this actually apply to me?"

Here's the thing...

[SECTION 2]
This is where it gets REALLY interesting.

[B-ROLL: Examples or demonstrations]

- Key insight 2
- Real-world application

[PATTERN INTERRUPT 2]
And this connects to something even bigger...

[SECTION 3]
The real breakthrough is this...

[B-ROLL: Visual summary of key point]

- The main takeaway
- Why this matters NOW

[CONCLUSION]
So here's your one action item...

If this changed how you think about this topic...
You'll definitely want to check out my video on [related topic].

[GESTURE: Point to video suggestion]
"""

        return {
            'script': script,
            'hook_options': [
                f"What if everything you knew about {video_data.get('title', 'this')} was wrong?",
                f"I spent 40 hours researching this... here's what nobody tells you.",
                f"The {selected_angle.get('angle_name', 'truth')} that experts don't want you to know."
            ],
            'titles': [
                f"The Truth About {video_data.get('title', 'This Topic')}",
                f"What They Don't Tell You About {video_data.get('title', 'This')}",
                f"I Analyzed {video_data.get('title', 'This')} - Here's What I Found",
                f"{selected_angle.get('angle_name')}: Deep Dive"
            ],
            'thumbnails': [
                "Shocked face + Red arrow pointing to key stat + Text: 'THE TRUTH'",
                "Split screen before/after + Yellow highlight + Text: 'EXPOSED'",
                "Creator pointing at screen + Graph going up + Text: 'PROOF'",
                "Crossed arms serious expression + Bold text + Text: 'WRONG'"
            ],
            'estimated_duration': '8-10 minutes',
            'word_count': len(script.split())
        }

    def format_script_for_display(self, script: str) -> str:
        """
        Format script for display with section markers, B-roll cues, and visual styling.

        Args:
            script: Raw script text

        Returns:
            Formatted script with clear sections and visual cues
        """
        import re

        # Main section markers with timing estimates
        section_formats = {
            '[HOOK]': '\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🎯 HOOK (0:00 - 0:08)\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n',
            '[INTRO]': '\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🎬 INTRODUCTION (0:08 - 0:30)\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n',
            '[SECTION 1]': '\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📝 SECTION 1 (~0:30 - 3:00)\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n',
            '[SECTION 2]': '\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📝 SECTION 2 (~3:00 - 5:30)\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n',
            '[SECTION 3]': '\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📝 SECTION 3 (~5:30 - 8:00)\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n',
            '[CONCLUSION]': '\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🎯 CONCLUSION & CTA (~8:00 - 9:00)\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n',
            # Legacy format support
            '[BODY]': '\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📝 MAIN CONTENT\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n',
        }

        # Pattern interrupt markers
        pattern_interrupt_formats = {
            '[PATTERN INTERRUPT 1]': '\n\n⚡ PATTERN INTERRUPT ⚡\n',
            '[PATTERN INTERRUPT 2]': '\n\n⚡ PATTERN INTERRUPT ⚡\n',
            '[PATTERN INTERRUPT]': '\n\n⚡ PATTERN INTERRUPT ⚡\n',
        }

        # Apply section formatting
        for marker, formatted in section_formats.items():
            script = script.replace(marker, formatted)

        # Apply pattern interrupt formatting
        for marker, formatted in pattern_interrupt_formats.items():
            script = script.replace(marker, formatted)

        # Format B-ROLL markers with visual styling
        # Match [B-ROLL: description] pattern
        def format_broll(match):
            description = match.group(1)
            return f'\n\n🎥 B-ROLL: {description}\n'

        script = re.sub(r'\[B-ROLL:\s*([^\]]+)\]', format_broll, script)

        # Format GESTURE markers
        def format_gesture(match):
            gesture = match.group(1)
            return f'\n👋 [{gesture}]\n'

        script = re.sub(r'\[GESTURE:\s*([^\]]+)\]', format_gesture, script)

        # Format PAUSE markers
        script = script.replace('[PAUSE]', '\n⏸️ [PAUSE]\n')

        return script
