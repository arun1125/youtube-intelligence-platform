"""
Research Synthesis Service

Uses Gemini to synthesize raw research data into a structured brief for script writing.
"""
from typing import Dict
import logging
import json

from google import genai

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ResearchSynthesisService:
    """Service for synthesizing research data using Gemini."""

    def __init__(self):
        """Initialize the research synthesis service."""
        api_key = settings.gemini_api_key or settings.google_api_key
        self.client = genai.Client(api_key=api_key)
        self.model = settings.gemini_model

    def _build_synthesis_prompt(
        self,
        video_data: Dict,
        selected_angle: Dict,
        raw_research: Dict,
        profile: Dict
    ) -> str:
        """
        Build the prompt for Gemini to synthesize research.

        Args:
            video_data: Original video details and transcript
            selected_angle: The angle user selected
            raw_research: Raw data from Exa, Perplexity, Firecrawl
            profile: Creator profile

        Returns:
            Formatted prompt string
        """
        # Format trending topics
        trending_topics_str = ""
        for i, topic in enumerate(raw_research.get('trending_topics', [])[:10], 1):
            trending_topics_str += f"\n{i}. {topic.get('title')}\n   URL: {topic.get('url')}\n   Summary: {topic.get('content', '')[:200]}...\n"

        # Format fact checks
        fact_checks_str = ""
        for check in raw_research.get('fact_checks', []):
            fact_checks_str += f"\nQuery: {check.get('query')}\nResponse: {check.get('verification', '')[:500]}...\n"

        # Format scraped content
        scraped_str = ""
        for i, content in enumerate(raw_research.get('scraped_content', [])[:5], 1):
            scraped_str += f"\n{i}. {content.get('url')}\n   Content: {content.get('content', '')[:300]}...\n"

        # Get transcript summary
        transcript = video_data.get('transcript', '')
        transcript_words = transcript.split()[:500]
        transcript_summary = ' '.join(transcript_words)

        prompt = f"""Analyze and synthesize this research data into a structured brief for script writing.

**Original Video:**
- Title: {video_data.get('title')}
- Views: {video_data.get('view_count'):,}
- Transcript Summary (first 500 words):
{transcript_summary}

**Selected Angle:**
- Name: {selected_angle.get('angle_name')}
- Hook: {selected_angle.get('core_hook')}
- Differentiator: {selected_angle.get('key_differentiator')}
- Target Emotion: {selected_angle.get('target_emotion')}

**Creator Profile:**
- Niche: {profile.get('niche')}
- Expertise: {', '.join(profile.get('expertise_areas', []))}
- Target Audience: {profile.get('target_audience')}

**Raw Research Data:**

Trending Topics (from Exa AI):
{trending_topics_str}

Fact Checks & Recent News (from Perplexity):
{fact_checks_str}

Scraped Content (from Firecrawl):
{scraped_str}

**Your Task:**
Synthesize this research into a structured brief for a script writer. Focus on:

1. Identify 5-8 NEW facts/data points NOT in the original video
2. Find contradictions or updates to original video claims
3. Extract compelling statistics, quotes, and examples
4. Organize by narrative flow (hook → introduction → body → conclusion)
5. Note which sources are most credible/relevant
6. Suggest 3 narrative hooks based on most compelling findings

**Output Format:**
Return ONLY valid JSON with this structure:

{{
  "executive_summary": "Brief overview of key findings (2-3 sentences)",
  "new_facts": [
    {{
      "fact": "The specific new fact or data point",
      "source": "URL or source name",
      "credibility": "high/medium/low",
      "placement_suggestion": "hook/introduction/body/conclusion"
    }}
  ],
  "updated_claims": [
    {{
      "original": "Claim from original video",
      "update": "New information or contradiction",
      "source": "URL or source name"
    }}
  ],
  "key_statistics": [
    {{
      "statistic": "The number/stat",
      "context": "What it means",
      "source": "URL or source name"
    }}
  ],
  "compelling_quotes": [
    {{
      "quote": "The actual quote",
      "attribution": "Who said it",
      "source": "URL or source name"
    }}
  ],
  "narrative_hooks": [
    "Hook option 1 (one sentence)",
    "Hook option 2 (one sentence)",
    "Hook option 3 (one sentence)"
  ],
  "supporting_evidence": [
    {{
      "point": "Main point to support in script",
      "evidence": "Supporting evidence",
      "source": "URL or source name"
    }}
  ]
}}
"""
        return prompt

    def synthesize_research(
        self,
        video_data: Dict,
        selected_angle: Dict,
        raw_research: Dict,
        profile: Dict
    ) -> Dict:
        """
        Synthesize raw research data into structured brief.

        Args:
            video_data: Original video details and transcript
            selected_angle: The angle user selected
            raw_research: Raw data from Exa, Perplexity, Firecrawl
            profile: Creator profile

        Returns:
            Dict with synthesized research brief
        """
        try:
            logger.info("Synthesizing research with Gemini...")

            # Build prompt
            prompt = self._build_synthesis_prompt(
                video_data,
                selected_angle,
                raw_research,
                profile
            )

            # Call Gemini
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )

            response_text = response.text.strip()

            # Parse JSON
            brief = self._parse_synthesis_response(response_text)

            if brief:
                logger.info("✓ Research synthesized successfully")
                return brief
            else:
                logger.error("Failed to parse synthesis response")
                return self._get_fallback_brief(raw_research)

        except Exception as e:
            logger.error(f"Error synthesizing research: {e}")
            return self._get_fallback_brief(raw_research)

    def _parse_synthesis_response(self, response_text: str) -> Dict:
        """
        Parse JSON response from Gemini.

        Args:
            response_text: Gemini's response

        Returns:
            Parsed research brief dict
        """
        try:
            # Remove markdown code blocks if present
            response_text = response_text.replace('```json', '').replace('```', '').strip()

            # Parse JSON
            brief = json.loads(response_text)

            # Validate structure
            required_keys = ['executive_summary', 'new_facts', 'narrative_hooks']
            if all(k in brief for k in required_keys):
                return brief

            logger.warning("Response missing required keys")
            return {}

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing synthesis: {e}")
            return {}

    def _get_fallback_brief(self, raw_research: Dict) -> Dict:
        """
        Get a minimal fallback brief if Gemini fails.

        Args:
            raw_research: Raw research data

        Returns:
            Basic research brief dict
        """
        logger.warning("Using fallback research brief")

        # Extract some basic facts from raw research
        new_facts = []
        for topic in raw_research.get('trending_topics', [])[:5]:
            new_facts.append({
                'fact': topic.get('title', 'Unknown'),
                'source': topic.get('url', 'Unknown'),
                'credibility': 'medium',
                'placement_suggestion': 'body'
            })

        return {
            'executive_summary': 'Research data compiled from multiple sources. Use the trending topics and fact-checks to enhance the script.',
            'new_facts': new_facts,
            'updated_claims': [],
            'key_statistics': [],
            'compelling_quotes': [],
            'narrative_hooks': [
                'What if everything you know about this is wrong?',
                'The data reveals something surprising...',
                'Here\'s what the experts aren\'t telling you...'
            ],
            'supporting_evidence': []
        }
