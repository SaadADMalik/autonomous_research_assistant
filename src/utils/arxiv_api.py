"""
arXivAPI Client - Fast, free academic paper search with no rate limits.

Coverage: 2.4M+ papers in physics, CS, math, stats, biology
Rate Limit: 1 request per 3 seconds (very generous)
Format: XML (Atom feed)
"""

import logging
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import quote

logger = logging.getLogger(__name__)


class ArxivAPI:
    """
    arXiv API client for fetching academic papers.
    
    No authentication required, very generous rate limits.
    Perfect for CS, physics, math, and quantum computing queries.
    """
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    # Rate limiting - arXiv asks for 3 seconds between requests
    MIN_REQUEST_INTERVAL = 3.0
    
    # XML namespaces
    NAMESPACES = {
        'atom': 'http://www.w3.org/2005/Atom',
        'arxiv': 'http://arxiv.org/schemas/atom'
    }
    
    def __init__(self):
        self.last_request_time = 0
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info("✅ ArxivAPI initialized (no auth required)")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    'User-Agent': 'AutonomousResearchAssistant/1.0 (Educational Research Tool)'
                }
            )
        return self.session
    
    async def _rate_limit(self):
        """Enforce rate limiting (3 seconds between requests)."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.MIN_REQUEST_INTERVAL:
            wait_time = self.MIN_REQUEST_INTERVAL - time_since_last
            logger.debug(f"⏳ Rate limiting: waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def search(
        self, 
        query: str, 
        max_results: int = 10,
        sort_by: str = "relevance"
    ) -> List[Dict]:
        """
        Search arXiv for papers.
        
        Args:
            query: Search query (supports boolean operators)
            max_results: Maximum number of results (default 10)
            sort_by: Sort order - "relevance", "lastUpdatedDate", "submittedDate"
            
        Returns:
            List of paper dictionaries with title, summary, authors, etc.
        """
        await self._rate_limit()
        
        # Build query URL
        # arXiv search syntax: all:quantum+computing (searches all fields)
        search_query = quote(f"all:{query}")
        sort_order = "relevance" if sort_by == "relevance" else "submittedDate"
        
        url = f"{self.BASE_URL}?search_query={search_query}&max_results={max_results}&sortBy={sort_order}&sortOrder=descending"
        
        logger.info(f"🔍 arXiv: Searching for '{query}' (max_results={max_results})")
        
        try:
            session = await self._get_session()
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    logger.error(f"❌ arXiv API error: HTTP {response.status}")
                    return []
                
                xml_content = await response.text()
                papers = self._parse_xml(xml_content)
                
                logger.info(f"✅ arXiv: Found {len(papers)} papers")
                return papers
                
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ arXiv: Timeout after 10 seconds")
            return []
        except Exception as e:
            logger.error(f"❌ arXiv API error: {e}")
            return []
    
    def _parse_xml(self, xml_content: str) -> List[Dict]:
        """
        Parse arXiv XML response into paper dictionaries.
        
        XML structure:
        <feed>
          <entry>
            <id>http://arxiv.org/abs/2103.12345v1</id>
            <title>Paper Title</title>
            <summary>Abstract text</summary>
            <author><name>John Doe</name></author>
            <published>2021-03-25T12:00:00Z</published>
            <link href="http://arxiv.org/abs/2103.12345v1" rel="alternate" type="text/html"/>
            <arxiv:primary_category term="cs.AI"/>
          </entry>
        </feed>
        """
        papers = []
        
        try:
            root = ET.fromstring(xml_content)
            entries = root.findall('atom:entry', self.NAMESPACES)
            
            if not entries:
                logger.warning("⚠️ arXiv: No entries found in XML response")
                return []
            
            for entry in entries:
                try:
                    # Extract paper ID from URL
                    paper_id = entry.find('atom:id', self.NAMESPACES)
                    paper_url = paper_id.text if paper_id is not None else ""
                    arxiv_id = paper_url.split('/abs/')[-1] if '/abs/' in paper_url else ""
                    
                    # Extract title (remove newlines and extra spaces)
                    title_elem = entry.find('atom:title', self.NAMESPACES)
                    title = title_elem.text.replace('\n', ' ').strip() if title_elem is not None else "Untitled"
                    
                    # Extract summary/abstract
                    summary_elem = entry.find('atom:summary', self.NAMESPACES)
                    summary = summary_elem.text.replace('\n', ' ').strip() if summary_elem is not None else ""
                    
                    # Extract authors
                    author_elems = entry.findall('atom:author/atom:name', self.NAMESPACES)
                    authors = [author.text for author in author_elems if author.text]
                    
                    # Extract publication date
                    published_elem = entry.find('atom:published', self.NAMESPACES)
                    published_date = published_elem.text if published_elem is not None else ""
                    year = int(published_date[:4]) if published_date and len(published_date) >= 4 else 2024
                    
                    # Extract category
                    category_elem = entry.find('arxiv:primary_category', self.NAMESPACES)
                    category = category_elem.get('term') if category_elem is not None else "unknown"
                    
                    # Build paper dictionary
                    paper = {
                        "title": title,
                        "summary": summary,
                        "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else paper_url,
                        "year": year,
                        "authors": authors,
                        "source": "arxiv",
                        "content_type": "research_paper",
                        "api_source": "arXiv API",
                        "arxiv_id": arxiv_id,
                        "category": category,
                        "citations": 0,  # arXiv doesn't provide citation counts
                        "venue": "arXiv preprint",
                        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    papers.append(paper)
                    logger.debug(f"   📄 Parsed: {title[:60]}...")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing arXiv entry: {e}")
                    continue
            
            return papers
            
        except ET.ParseError as e:
            logger.error(f"❌ XML parsing error: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error parsing XML: {e}")
            return []
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("🔒 ArxivAPI session closed")
    
    def __del__(self):
        """Cleanup on deletion."""
        if self.session and not self.session.closed:
            try:
                asyncio.get_event_loop().run_until_complete(self.close())
            except:
                pass
