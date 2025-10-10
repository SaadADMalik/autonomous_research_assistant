import logging
import aiohttp
import xml.etree.ElementTree as ET
from typing import List
from src.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class DataFetcher:
    async def fetch_arxiv(self, query: str, max_results: int = 5) -> List[str]:
        logger.info(f"Fetching Arxiv data for query: {query}")
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://export.arxiv.org/api/query?search_query=all:{query}&max_results={max_results}"
                async with session.get(url) as response:
                    if response.status == 200:
                        text = await response.text()
                        root = ET.fromstring(text)
                        documents = []
                        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                            title = entry.find('{http://www.w3.org/2005/Atom}title').text
                            summary = entry.find('{http://www.w3.org/2005/Atom}summary').text
                            documents.append(f"{title}: {summary}")
                        logger.info(f"Fetched {len(documents)} Arxiv documents")
                        return documents
                    else:
                        logger.error(f"Arxiv API request failed with status {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching Arxiv data: {str(e)}")
            return []