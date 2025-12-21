"""
Research Service

Gathers research data from Exa AI, Perplexity, and Firecrawl for script enhancement.
"""
from typing import List, Dict, Optional
import logging

from exa_py import Exa
from openai import OpenAI  # Perplexity uses OpenAI-compatible API
from firecrawl import FirecrawlApp

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ResearchService:
    """Service for gathering research data from multiple sources."""

    def __init__(self):
        """Initialize the research service with API clients."""
        self.exa = Exa(api_key=settings.exa_api_key)

        # Perplexity uses OpenAI-compatible API
        self.perplexity = OpenAI(
            api_key=settings.perplexity_api_key,
            base_url="https://api.perplexity.ai"
        )

        self.firecrawl = FirecrawlApp(api_key=settings.firecrawl_api_key)

    def _exa_search(self, query: str, num_results: int = 10) -> Dict:
        """
        Search for trending topics using Exa AI.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            Dict with search results
        """
        try:
            logger.info(f"Exa search: {query}")

            # Use Exa's neural search with autoprompt
            search_response = self.exa.search_and_contents(
                query,
                num_results=num_results,
                use_autoprompt=True,
                text=True
            )

            results = []
            for result in search_response.results:
                results.append({
                    'title': result.title,
                    'url': result.url,
                    'content': result.text[:2000] if result.text else '',  # Limit content
                    'score': getattr(result, 'score', 0)
                })

            logger.info(f"✓ Exa returned {len(results)} results")

            return {
                'success': True,
                'results': results,
                'query': query
            }

        except Exception as e:
            logger.error(f"Exa search error: {e}")
            return {
                'success': False,
                'results': [],
                'query': query,
                'error': str(e)
            }

    def _perplexity_search(self, query: str) -> Dict:
        """
        Get fact-checking and recent news from Perplexity.

        Args:
            query: Research query

        Returns:
            Dict with Perplexity response
        """
        try:
            logger.info(f"Perplexity search: {query}")

            # Use Perplexity's sonar model for real-time research
            response = self.perplexity.chat.completions.create(
                model="sonar",
                messages=[{
                    "role": "user",
                    "content": query
                }]
            )

            content = response.choices[0].message.content

            logger.info(f"✓ Perplexity returned {len(content)} chars")

            return {
                'success': True,
                'content': content,
                'query': query
            }

        except Exception as e:
            logger.error(f"Perplexity search error: {e}")
            return {
                'success': False,
                'content': '',
                'query': query,
                'error': str(e)
            }

    def _firecrawl_scrape(self, url: str) -> Dict:
        """
        Scrape content from a URL using Firecrawl.

        Args:
            url: URL to scrape

        Returns:
            Dict with scraped content
        """
        try:
            logger.info(f"Firecrawl scraping: {url}")

            # Scrape the URL
            result = self.firecrawl.scrape_url(
                url,
                params={'formats': ['markdown', 'html']}
            )

            content = result.get('markdown', result.get('html', ''))

            logger.info(f"✓ Firecrawl scraped {len(content)} chars")

            return {
                'success': True,
                'url': url,
                'content': content[:5000],  # Limit content
                'metadata': result.get('metadata', {})
            }

        except Exception as e:
            logger.error(f"Firecrawl scrape error for {url}: {e}")
            return {
                'success': False,
                'url': url,
                'content': '',
                'error': str(e)
            }

    def gather_research(
        self,
        video_topic: str,
        niche: str,
        transcript_summary: str,
        claims: Optional[List[str]] = None
    ) -> Dict:
        """
        Gather research from all sources.

        Args:
            video_topic: Main topic of the video
            niche: Creator's niche
            transcript_summary: Summary of video transcript
            claims: Optional list of claims to fact-check

        Returns:
            Dict with raw research data from all sources
        """
        logger.info(f"Gathering research for topic: {video_topic}")

        research_data = {
            'video_topic': video_topic,
            'niche': niche,
            'trending_topics': [],
            'fact_checks': [],
            'new_data': [],
            'scraped_content': []
        }

        # 1. Exa AI: Find trending topics in niche
        exa_query = f"trending topics about {video_topic} in {niche} 2024 2025"
        exa_results = self._exa_search(exa_query, num_results=10)

        if exa_results['success']:
            research_data['trending_topics'] = exa_results['results']

            # Extract URLs for scraping
            urls_to_scrape = [r['url'] for r in exa_results['results'][:5]]
        else:
            urls_to_scrape = []

        # 2. Perplexity: Fact-check and find recent news
        if claims:
            # Fact-check specific claims
            claims_text = '\n'.join([f"- {claim}" for claim in claims])
            perplexity_query = f"""Verify these claims and find recent data/news about them:
{claims_text}

Provide sources and any updates or contradictions."""
        else:
            # General research query
            perplexity_query = f"""Find recent news, data, and developments about: {video_topic}

Focus on:
- New statistics or research findings
- Recent events or updates
- Expert opinions
- Contrarian viewpoints

Provide sources."""

        perplexity_results = self._perplexity_search(perplexity_query)

        if perplexity_results['success']:
            research_data['fact_checks'].append({
                'query': perplexity_query,
                'verification': perplexity_results['content'],
                'source': 'Perplexity AI'
            })

        # 3. Firecrawl: Scrape URLs from Exa
        for url in urls_to_scrape:
            scraped = self._firecrawl_scrape(url)
            if scraped['success']:
                research_data['scraped_content'].append(scraped)

        # Log summary
        logger.info(f"""✓ Research gathered:
- Trending topics: {len(research_data['trending_topics'])}
- Fact checks: {len(research_data['fact_checks'])}
- Scraped pages: {len(research_data['scraped_content'])}
""")

        return research_data

    def extract_claims_from_transcript(self, transcript: str, max_claims: int = 5) -> List[str]:
        """
        Extract key claims from a transcript for fact-checking.

        This is a simple extraction - just gets first few sentences
        that look like claims. Could be enhanced with NLP.

        Args:
            transcript: Video transcript
            max_claims: Maximum claims to extract

        Returns:
            List of claim strings
        """
        # Simple heuristic: look for sentences with numbers, "is", "are", etc.
        sentences = transcript.split('.')
        claims = []

        keywords = ['is', 'are', 'was', 'were', 'will', 'has', 'have', '%', 'million', 'billion']

        for sentence in sentences[:50]:  # Check first 50 sentences
            sentence = sentence.strip()
            if len(sentence) < 20:  # Too short
                continue
            if len(sentence) > 200:  # Too long
                continue

            # Check if contains keywords
            if any(keyword in sentence.lower() for keyword in keywords):
                claims.append(sentence)

            if len(claims) >= max_claims:
                break

        return claims
