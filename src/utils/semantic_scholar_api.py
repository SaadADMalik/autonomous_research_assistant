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
            self.min_request_interval = 1.0
            logger.info("🔑 Using Semantic Scholar API key")
        else:
            self.min_request_interval = 2.0
            logger.info("🔓 Using Semantic Scholar without API key")
        
        self.storage = DataStorage()
        self.last_request_time = 0
        self.timeout = 30
    
    async def _rate_limit(self):
        """Enforce rate limiting to avoid API blocks."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"⏳ Rate limiting: sleeping {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search Semantic Scholar for papers.
        Returns list of papers or empty list on failure.
        """
        logger.info(f"🔍 Searching Semantic Scholar: '{query}'")
        
        if not query or not query.strip():
            logger.error("❌ Empty query provided")
            return []
        
        # Apply rate limiting
        await self._rate_limit()
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/paper/search"
                params = {
                    "query": query.strip(),
                    "limit": max_results,
                    "fields": "title,abstract,authors,year,url,citationCount,venue,publicationDate,externalIds"
                }
                
                logger.debug(f"📡 API URL: {url}")
                logger.debug(f"📋 Parameters: {params}")
                
                try:
                    async with session.get(
                        url, 
                        headers=self.headers, 
                        params=params, 
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        logger.debug(f"📊 HTTP Status: {response.status}")
                        
                        # Handle rate limiting
                        if response.status == 429:
                            logger.warning(f"⚠️ Rate limited by Semantic Scholar")
                            return []
                        
                        # Handle unauthorized
                        if response.status == 401:
                            logger.error(f"❌ API key invalid or expired")
                            return []
                        
                        # Handle server errors
                        if response.status >= 500:
                            logger.error(f"❌ Semantic Scholar server error: {response.status}")
                            return []
                        
                        # Handle client errors
                        if response.status >= 400:
                            logger.error(f"❌ API error {response.status}")
                            return []
                        
                        if response.status != 200:
                            logger.error(f"❌ Unexpected status: {response.status}")
                            return []
                        
                        try:
                            data = await response.json()
                        except asyncio.TimeoutError:
                            logger.error(f"⏰ Timeout reading response")
                            return []
                        except Exception as e:
                            logger.error(f"❌ Failed to parse JSON: {str(e)}")
                            return []
                        
                        papers = data.get("data", [])
                        logger.info(f"📋 Received {len(papers)} papers from API")
                        
                        if not papers:
                            logger.warning(f"📭 No papers found for query")
                            return []
                        
                        results = []
                        for i, paper in enumerate(papers):
                            try:
                                result = self._parse_paper(paper, query)
                                if result:
                                    results.append(result)
                                    logger.debug(f"✅ Paper {i+1}: {result['title'][:50]}...")
                                else:
                                    logger.debug(f"⚠️ Paper {i+1}: Skipped (missing required fields)")
                                    
                            except Exception as e:
                                logger.debug(f"⚠️ Error parsing paper {i+1}: {str(e)}")
                                continue
                        
                        logger.info(f"✅ Processed {len(results)} valid papers")
                        return results
                        
                except asyncio.TimeoutError:
                    logger.error(f"⏰ Request timeout after {self.timeout}s")
                    return []
                except aiohttp.ClientError as e:
                    logger.error(f"❌ Network error: {str(e)}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ Critical error in search: {str(e)}", exc_info=True)
            return []
    
    def _parse_paper(self, paper: dict, query: str) -> dict:
        """
        Parse a paper from Semantic Scholar API response.
        Validates all required fields.
        """
        try:
            # Validate title
            title = paper.get("title", "").strip()
            if not title:
                return None
            
            # Validate abstract
            abstract = paper.get("abstract", "").strip()
            if not abstract:
                logger.debug("⚠️ Paper missing abstract")
                return None
            
            # Extract authors
            authors = []
            for author in paper.get("authors", []):
                author_name = author.get("name", "").strip()
                if author_name and author_name.lower() != "unknown":
                    authors.append(clean_text(author_name))
            
            if not authors:
                authors = ["Unknown Author"]
            
            # Extract URL
            paper_url = paper.get("url", "").strip()
            if not paper_url and paper.get("externalIds", {}).get("DOI"):
                paper_url = f"https://doi.org/{paper['externalIds']['DOI']}"
            
            # Extract year
            year = paper.get("year")
            if not year:
                pub_date = paper.get("publicationDate", "")
                if pub_date:
                    try:
                        year = int(pub_date[:4])
                    except (ValueError, TypeError):
                        year = datetime.now().year
                else:
                    year = datetime.now().year
            
            # Build result
            result = {
                **create_metadata("semantic_scholar", query),
                "title": clean_text(title),
                "summary": clean_text(abstract),
                "abstract": clean_text(abstract),
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
            
            # Save to storage
            try:
                asyncio.create_task(self.storage.save_raw_data(result))
                asyncio.create_task(self.storage.save_processed_data(result))
            except Exception as e:
                logger.debug(f"⚠️ Failed to save paper to storage: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.debug(f"⚠️ Error parsing paper: {str(e)}")
            return None