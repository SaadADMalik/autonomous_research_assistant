import arxiv
import time
from typing import List, Dict
from .preprocessing import clean_text, create_metadata
from .storage import DataStorage

class ArxivAPI:
    def __init__(self):
        self.client = arxiv.Client()
        self.last_request_time = 0
        self.min_request_interval = 3  # seconds between requests
        self.storage = DataStorage()

    def _rate_limit(self) -> None:
        """Basic rate limiting implementation."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = current_time

    async def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search arXiv and return paper details."""
        self._rate_limit()
        
        try:
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )

            results = []
            for paper in self.client.results(search):
                metadata = create_metadata("arxiv", query)
                
                data = {
                    **metadata,
                    "title": paper.title,
                    "authors": [author.name for author in paper.authors],
                    "summary": clean_text(paper.summary),
                    "url": paper.pdf_url,
                    "published": paper.published.strftime("%Y-%m-%d"),
                    "categories": paper.categories
                }
                
                # Save both raw and processed data
                await self.storage.save_raw_data(data)
                await self.storage.save_processed_data(data)
                results.append(data)
                
            return results

        except Exception as e:
            print(f"Error accessing arXiv: {str(e)}")
            return []