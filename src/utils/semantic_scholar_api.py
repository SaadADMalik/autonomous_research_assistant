import aiohttp
import logging
import asyncio
import time
from typing import List, Dict
import urllib.parse
from datetime import datetime
from .preprocessing import clean_text, create_metadata
from .storage import DataStorage
from .logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class SemanticScholarAPI:
    def __init__(self, api_key: str = None):
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.headers = {
            "User-Agent": "AIResearchAssistant/1.0 (saadadmalik@example.com)"
        }
        
        # Add API key if provided
        if api_key:
            self.headers["x-api-key"] = api_key
            self.min_request_interval = 1.0  # 1 request per second with key
            logger.info("🔑 Using Semantic Scholar API key")
        else:
            self.min_request_interval = 2.0  # Slower without key
            logger.info("🔓 Using Semantic Scholar without API key")
        
        self.storage = DataStorage()
        self.last_request_time = 0
    
    async def _rate_limit(self):
        """Ensure we don't hit rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"⏳ Rate limiting: sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search Semantic Scholar for papers."""
        logger.info(f"🔍 Searching Semantic Scholar for: '{query}'")
        
        # Apply rate limiting
        await self._rate_limit()
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/paper/search"
                params = {
                    "query": query,
                    "limit": max_results,
                    "fields": "title,abstract,authors,year,url,citationCount,venue,publicationDate,externalIds"
                }
                
                logger.debug(f"📡 Semantic Scholar URL: {url}")
                
                async with session.get(url, headers=self.headers, params=params, timeout=30) as response:
                    logger.debug(f"📊 Semantic Scholar status: {response.status}")
                    
                    if response.status == 429:
                        logger.warning(f"⚡ RATE LIMITED: Semantic Scholar API (query: '{query}')")
                        return []  # This triggers educational fallback
                    
                    if response.status != 200:
                        logger.error(f"❌ API ERROR: Semantic Scholar returned {response.status}")
                        response_text = await response.text()
                        logger.error(f"Error response: {response_text[:500]}")
                        return []
                    
                    data = await response.json()
                    papers = data.get("data", [])
                    logger.info(f"📋 Semantic Scholar returned {len(papers)} raw papers")
                    
                    results = []
                    for i, paper in enumerate(papers):
                        try:
                            # Skip papers without abstracts
                            abstract = paper.get("abstract")
                            if not abstract:
                                logger.debug(f"📄 Paper {i+1}: No abstract, skipping")
                                continue
                            
                            # Extract authors
                            authors = []
                            for author in paper.get("authors", []):
                                author_name = author.get("name", "Unknown")
                                if author_name != "Unknown":
                                    authors.append(clean_text(author_name))
                            
                            if not authors:
                                authors = ["Unknown Author"]
                            
                            # Create proper URL
                            paper_url = paper.get("url", "")
                            if not paper_url and paper.get("externalIds", {}).get("DOI"):
                                paper_url = f"https://doi.org/{paper['externalIds']['DOI']}"
                            
                            # Extract year
                            year = paper.get("year")
                            if not year:
                                pub_date = paper.get("publicationDate")
                                if pub_date:
                                    try:
                                        year = int(pub_date[:4])
                                    except:
                                        year = datetime.now().year
                                else:
                                    year = datetime.now().year
                            
                            result = {
                                **create_metadata("semantic_scholar", query),
                                "title": clean_text(paper.get("title", "Untitled")),
                                "summary": clean_text(abstract),
                                "url": paper_url,
                                "year": year,
                                "authors": authors,
                                "citations": paper.get("citationCount", 0),
                                "venue": paper.get("venue", ""),
                                "categories": ["semantic_scholar"],
                                "source": "semantic_scholar",
                                "content_type": "real_research",
                                "api_source": "Semantic Scholar API",
                                "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            logger.debug(f"✅ Successfully processed paper {i+1}: {result['title'][:50]}...")
                            
                            # Save to storage
                            await self.storage.save_raw_data(result)
                            await self.storage.save_processed_data(result)
                            
                            results.append(result)
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Error processing paper {i+1}: {str(e)}")
                            continue
                    
                    if results:
                        logger.info(f"✅ REAL PAPERS: Successfully processed {len(results)} papers from Semantic Scholar")
                    else:
                        logger.warning(f"📭 NO VALID PAPERS: All papers from Semantic Scholar lacked abstracts")
                    
                    return results
                    
        except asyncio.TimeoutError:
            logger.error(f"⏰ TIMEOUT: Semantic Scholar API request timed out for query: '{query}'")
            return []
        except Exception as e:
            logger.error(f"❌ SEMANTIC SCHOLAR ERROR: {str(e)}", exc_info=True)
            return []