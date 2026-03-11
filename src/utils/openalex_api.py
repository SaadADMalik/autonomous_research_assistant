"""
OpenAlex API Client - Free, comprehensive academic search across all disciplines.

Coverage: 250M+ papers across ALL fields (medicine, CS, biology, etc.)
Rate Limit: 10 requests/second with polite pool (email in User-Agent)
Format: JSON (modern, easy to parse)
"""

import logging
import asyncio
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import quote

logger = logging.getLogger(__name__)


class OpenAlexAPI:
    """
    OpenAlex API client for fetching academic papers.
    
    No authentication required. Very generous rate limits (10 RPS).
    Excellent coverage across all academic disciplines.
    """
    
    BASE_URL = "https://api.openalex.org/works"
    
    # Rate limiting - 10 requests/second with polite pool
    MIN_REQUEST_INTERVAL = 0.1  # 100ms = 10 RPS
    
    # Email for polite pool (gets better rate limits)
    CONTACT_EMAIL = "researcher@autonomous-ai.edu"
    
    # API Key for higher rate limits (100 req/sec vs 10 req/sec)
    API_KEY = "VtTL2uEKq5an9RlGeOvvrq"  # Free tier: $1/day = 1000 searches
    
    def __init__(self):
        self.last_request_time = 0
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info("✅ OpenAlexAPI initialized with API key (100 RPS, $1/day free)")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with polite pool headers."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    'User-Agent': f'AutonomousResearchAssistant/1.0 (mailto:{self.CONTACT_EMAIL})',
                    'Accept': 'application/json'
                }
            )
        return self.session
    
    async def _rate_limit(self):
        """Enforce rate limiting (10 requests/second)."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.MIN_REQUEST_INTERVAL:
            wait_time = self.MIN_REQUEST_INTERVAL - time_since_last
            logger.debug(f"⏳ Rate limiting: waiting {wait_time*1000:.0f}ms")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def search(
        self, 
        query: str, 
        max_results: int = 10,
        sort: str = "relevance_score:desc"
    ) -> List[Dict]:
        """
        Search OpenAlex for papers with detailed performance logging.
        
        Args:
            query: Search query (natural language)
            max_results: Maximum number of results (default 10)
            sort: Sort order - "relevance_score:desc", "publication_date:desc", "cited_by_count:desc"
            
        Returns:
            List of paper dictionaries with title, summary, authors, etc.
        """
        await self._rate_limit()
        
        # Start performance timing
        search_start = asyncio.get_event_loop().time()
        
        # Build query URL
        # OpenAlex uses 'search' parameter for full-text search
        # NOTE: 🚨 Sort parameter causes 0 results when combined with search! Using default relevance sort instead.
        params = {
            'search': query,
            'per_page': min(max_results, 50),  # Max 50 per request
            'api_key': self.API_KEY  # 🔑 Add API key for better rate limits
        }
        
        # Don't add filter - causes compatibility issues with sort
        url = f"{self.BASE_URL}?search={quote(query)}&per_page={params['per_page']}&api_key={self.API_KEY}"
        
        logger.info(f"🔍 OpenAlex: Searching for '{query}' (max_results={max_results})")
        logger.info(f"🌐 OpenAlex URL: {url}")  # 🐛 DEBUG: Log actual URL
        
        try:
            session = await self._get_session()
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.error(f"❌ OpenAlex API error: HTTP {response.status}")
                    return []
                
                data = await response.json()
                logger.info(f"🐛 OpenAlex raw results count: {len(data.get('results', []))}")  # DEBUG
                papers = self._parse_response(data)
                
                # Log API fetch performance
                fetch_duration = asyncio.get_event_loop().time() - search_start
                if len(papers) == 0:
                    logger.warning(f"⚠️ OpenAlex: No results found")
                logger.info(f"⏱️  OpenAlex API fetch: {fetch_duration:.2f}s ({len(papers)} papers)")
                
                return papers
                
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ OpenAlex: Timeout after 10 seconds")
            return []
        except Exception as e:
            logger.error(f"❌ OpenAlex API error: {e}")
            return []
    
    def _parse_response(self, data: dict) -> List[Dict]:
        """
        Parse OpenAlex JSON response into paper dictionaries.
        
        Response structure:
        {
          "results": [
            {
              "id": "https://openalex.org/W1234567890",
              "title": "Paper Title",
              "abstract_inverted_index": {...},
              "authorships": [{"author": {"display_name": "John Doe"}}],
              "publication_date": "2021-03-25",
              "primary_location": {"source": {"display_name": "Nature"}},
              "cited_by_count": 42,
              "doi": "10.1234/example"
            }
          ]
        }
        """
        papers = []
        
        results = data.get('results', [])
        
        if not results:
            logger.warning("⚠️ OpenAlex: No results found")
            return []
        
        for result in results:
            try:
                # Extract basic info
                title = result.get('title', 'Untitled')
                if not title:
                    continue
                
                # Extract abstract (OpenAlex uses inverted index format)
                abstract = self._reconstruct_abstract(result.get('abstract_inverted_index', {}))
                
                # Skip papers with metadata-only abstracts (e.g. "Udgivelsesdato: September 2006")
                # These are papers where OpenAlex stored publication date metadata instead of the abstract
                if abstract:
                    import re as _re
                    # Skip if abstract is too short to be meaningful (<15 words)
                    if len(abstract.split()) < 15:
                        logger.debug(f"   ⏭️ Skipping short abstract: '{abstract[:60]}'")
                        continue
                    # Skip publication metadata patterns like "Udgivelsesdato: September 2006"
                    if _re.match(r'^\w+:\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', abstract):
                        logger.debug(f"   ⏭️ Skipping metadata-only abstract: '{abstract[:60]}'")
                        continue
                
                # Extract DOI and construct URL
                doi = result.get('doi', '')
                paper_url = doi if doi else result.get('id', '')
                
                # Extract authors (handle None values)
                authorships = result.get('authorships', [])
                authors = []
                if authorships:
                    for auth in authorships[:10]:  # Limit to first 10 authors
                        if auth and isinstance(auth, dict):
                            author_obj = auth.get('author')
                            if author_obj and isinstance(author_obj, dict):
                                name = author_obj.get('display_name')
                                if name:
                                    authors.append(name)
                
                # Extract publication year
                pub_date = result.get('publication_date', '')
                year = int(pub_date[:4]) if pub_date and len(pub_date) >= 4 else 2024
                
                # Extract venue/journal (handle None values)
                primary_location = result.get('primary_location')
                venue = 'Unknown Venue'
                if primary_location and isinstance(primary_location, dict):
                    source = primary_location.get('source')
                    if source and isinstance(source, dict):
                        venue = source.get('display_name', 'Unknown Venue')
                
                # Extract citation count
                citations = result.get('cited_by_count', 0)
                
                # Extract concepts/topics for domain classification
                concepts = result.get('concepts', [])
                primary_concept = concepts[0].get('display_name', 'unknown') if concepts else 'unknown'
                
                # Skip non-English content (OpenAlex language metadata is sometimes wrong)
                text_to_check = (title + " " + abstract)[:200]
                non_ascii = sum(1 for c in text_to_check if ord(c) > 127)
                if len(text_to_check) > 10 and non_ascii / len(text_to_check) > 0.05:
                    logger.debug(f"   🌍 Skipping non-English paper: {title[:50]}")
                    continue

                # Build paper dictionary
                paper = {
                    "title": title,
                    "summary": abstract if abstract else title,  # Fallback to title if no abstract
                    "url": paper_url,
                    "year": year,
                    "authors": authors,
                    "source": "openalex",
                    "content_type": "research_paper",
                    "api_source": "OpenAlex API",
                    "openalex_id": result.get('id', ''),
                    "doi": doi,
                    "venue": venue,
                    "citations": citations,
                    "primary_topic": primary_concept,
                    "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                papers.append(paper)
                logger.debug(f"   📄 Parsed: {title[:60]}... (citations: {citations})")
                
            except Exception as e:
                logger.warning(f"⚠️ Error parsing OpenAlex entry: {e}")
                continue
        
        return papers
    
    def _reconstruct_abstract(self, inverted_index: dict) -> str:
        """
        Reconstruct abstract from OpenAlex inverted index format.
        
        Inverted index: {"word1": [0, 5], "word2": [1, 3]}
        Means: word1 appears at positions 0 and 5, word2 at positions 1 and 3
        """
        if not inverted_index:
            return ""
        
        try:
            # Build list of (position, word) tuples
            word_positions = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            
            # Sort by position and join
            word_positions.sort(key=lambda x: x[0])
            abstract = ' '.join(word for _, word in word_positions)
            
            # Truncate if too long (some abstracts are huge)
            if len(abstract) > 2000:
                abstract = abstract[:2000] + "..."
            
            return abstract
            
        except Exception as e:
            logger.warning(f"⚠️ Error reconstructing abstract: {e}")
            return ""
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("🔒 OpenAlexAPI session closed")
    
    def __del__(self):
        """Cleanup on deletion."""
        if self.session and not self.session.closed:
            try:
                asyncio.get_event_loop().run_until_complete(self.close())
            except:
                pass
