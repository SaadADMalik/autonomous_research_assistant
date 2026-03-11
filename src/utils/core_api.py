"""
CORE API Client

Free access to 200+ million open access research papers from repositories worldwide.
No authentication required, generous rate limits.

API Docs: https://core.ac.uk/documentation/api
Search Guide: https://core.ac.uk/services/api
"""

import logging
import asyncio
import aiohttp
from urllib.parse import quote
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class CoreAPI:
    """
    CORE (COnnecting REpositories) API client for open access research papers.
    
    Coverage: 200M+ papers from 10,000+ data providers worldwide
    Rate Limit: Very generous (no strict limit, be polite)
    Best For: Open access papers, all disciplines, institutional repositories
    Cost: FREE (no authentication required for basic search)
    
    Features:
    - Searches across global open access repositories
    - Full abstracts available
    - Download links to full PDFs when available
    - Good coverage of preprints and working papers
    """
    
    # API Configuration
    BASE_URL = "https://api.core.ac.uk/v3"
    MIN_REQUEST_INTERVAL = 0.5  # 500ms = 2 req/sec (polite, no official limit)
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize CORE API client.
        
        Args:
            api_key: Optional CORE API key (get free at https://core.ac.uk/services/api#api-keys)
                     Not required for basic search, but provides higher rate limits
        """
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request_time = 0
        
        if api_key:
            logger.info("✅ CoreAPI initialized with API key (higher rate limits)")
        else:
            logger.info("✅ CoreAPI initialized (polite pool: 2 RPS, no auth)")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session (reuse across requests)."""
        if self._session is None or self._session.closed:
            headers = {
                # 🎯 FIX: Prevent zstd encoding error - aiohttp doesn't support zstd by default
                # CORE API sends zstd-compressed responses which causes HTTP 400 error
                "Accept-Encoding": "gzip, deflate"  # Only accept supported encodings
            }
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session
    
    async def _rate_limit(self):
        """Enforce rate limiting to be nice to CORE servers."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.MIN_REQUEST_INTERVAL:
            await asyncio.sleep(self.MIN_REQUEST_INTERVAL - time_since_last)
        
        self._last_request_time = asyncio.get_event_loop().time()
    
    async def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search CORE for open access papers matching query.
        
        Args:
            query: Search query (e.g., "renewable energy policy impacts")
            max_results: Maximum papers to return (default 10, max 100)
            
        Returns:
            List of paper dictionaries with keys:
            - title, summary (abstract), authors, url, publish_date, source, citations
        """
        await self._rate_limit()
        
        search_start = asyncio.get_event_loop().time()
        
        logger.info(f"🔍 CORE: Searching for '{query}' (max_results={max_results})")
        
        try:
            # Build search request
            # CORE v3 uses POST for search
            url = f"{self.BASE_URL}/search/works"
            
            payload = {
                "q": query,
                "limit": min(max_results, 100),  # Max 100 per request
                "scroll": False,  # Don't use scrolling for simple searches
                "exclude": ["fullText"]  # Exclude full text to speed up response
            }
            
            session = await self._get_session()
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 500:
                    logger.warning(f"⚠️ CORE: HTTP 500 (server error) - CORE servers experiencing issues")
                    return []
                elif response.status != 200:
                    logger.error(f"❌ CORE API error: HTTP {response.status}")
                    return []
                
                data = await response.json()
                papers = self._parse_response(data)
                
                fetch_duration = asyncio.get_event_loop().time() - search_start
                if papers:
                    logger.info(f"⏱️  CORE API fetch: {fetch_duration:.2f}s ({len(papers)} papers)")
                else:
                    logger.warning(f"⚠️ CORE: No papers found in {fetch_duration:.2f}s")
                
                return papers
                
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ CORE: Timeout after 15 seconds")
            return []
        except Exception as e:
            logger.error(f"❌ CORE API error: {e}")
            return []
    
    def _parse_response(self, data: dict) -> List[Dict]:
        """
        Parse CORE JSON response into paper dictionaries.
        
        Response structure:
        {
          "totalHits": 12345,
          "results": [
            {
              "title": "Paper Title",
              "abstract": "Full abstract text...",
              "authors": ["Author One", "Author Two"],
              "downloadUrl": "https://...",
              "yearPublished": 2023,
              "publisher": "Publisher Name",
              "sourceFulltextUrls": [...]
            }
          ]
        }
        """
        papers = []
        results = data.get('results', [])
        
        if not results:
            logger.warning("⚠️ CORE: No results found")
            return []
        
        for result in results:
            try:
                # Extract basic info
                title = result.get('title', 'Untitled')
                if not title or title == 'Untitled':
                    continue
                
                # Extract abstract
                abstract = result.get('abstract', '')
                if not abstract:
                    # Try description field as fallback
                    abstract = result.get('description', '')
                
                # Skip papers without abstracts
                if not abstract or len(abstract.strip()) < 50:
                    logger.debug(f"   ⏭️ Skipping paper without abstract: '{title[:60]}'")
                    continue
                
                # Clean abstract (remove excessive whitespace)
                abstract = ' '.join(abstract.split())
                
                # Extract authors
                authors = result.get('authors', [])
                if isinstance(authors, list):
                    # Authors might be strings or objects
                    author_names = []
                    for author in authors[:10]:  # Limit to first 10
                        if isinstance(author, str):
                            author_names.append(author)
                        elif isinstance(author, dict):
                            name = author.get('name', '')
                            if name:
                                author_names.append(name)
                    authors = author_names
                else:
                    authors = []
                
                # Extract publication info
                year = result.get('yearPublished', 'Unknown')
                publisher = result.get('publisher', result.get('journals', [''])[0] if result.get('journals') else 'Unknown')
                
                # Get URL (prefer downloadUrl, fallback to other URLs)
                paper_url = result.get('downloadUrl') or \
                           result.get('doi') or \
                           (result.get('sourceFulltextUrls', [''])[0] if result.get('sourceFulltextUrls') else '') or \
                           f"https://core.ac.uk/works/{result.get('id', '')}"
                
                # Get citation count if available
                citations = result.get('citationCount', 0)
                
                paper = {
                    "title": title,
                    "summary": abstract,
                    "authors": authors,
                    "url": paper_url,
                    "publish_date": str(year),
                    "source": f"CORE ({publisher})",
                    "citations": citations
                }
                
                papers.append(paper)
                
            except Exception as e:
                logger.warning(f"⚠️ Error parsing CORE entry: {e}")
                continue
        
        logger.debug(f"   Parsed {len(papers)} papers (filtered from {len(results)} total)")
        return papers
    
    async def close(self):
        """Close aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("🔒 CoreAPI session closed")


# Example usage
if __name__ == "__main__":
    async def test():
        api = CoreAPI()  # or CoreAPI(api_key="YOUR_KEY")
        
        test_queries = [
            "artificial intelligence ethics",
            "quantum computing algorithms",
            "climate change mitigation strategies"
        ]
        
        for query in test_queries:
            print(f"\n{'='*80}")
            print(f"Query: '{query}'")
            print('='*80)
            
            papers = await api.search(query, max_results=3)
            
            print(f"\n✅ Found {len(papers)} papers\n")
            for i, paper in enumerate(papers, 1):
                print(f"{i}. {paper['title'][:100]}...")
                print(f"   Authors: {', '.join(paper['authors'][:3])}")
                print(f"   Source: {paper['source']}")
                print(f"   URL: {paper['url']}")
                print(f"   Abstract: {paper['summary'][:150]}...\n")
        
        await api.close()
    
    asyncio.run(test())
