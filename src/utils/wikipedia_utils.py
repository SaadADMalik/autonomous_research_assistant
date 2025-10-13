import wikipediaapi
import time
from typing import Dict, Optional, List
from .preprocessing import clean_text, create_metadata
from .storage import DataStorage

class WikipediaAPI:
    def __init__(self, user_agent: str = "research_assistant/1.0"):
        self.wiki = wikipediaapi.Wikipedia(
            user_agent=user_agent,
            language='en'
        )
        self.last_request_time = 0
        self.min_request_interval = 1
        self.storage = DataStorage()

    def _rate_limit(self) -> None:
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = current_time

    async def search(self, query: str) -> Optional[Dict]:
        self._rate_limit()
        
        try:
            page = self.wiki.page(query)
            if not page.exists():
                return None

            content = clean_text(page.text)
            metadata = create_metadata("wikipedia", query)
            
            data = {
                **metadata,
                "title": page.title,
                "summary": content,  # Normalize to "summary"
                "url": page.fullurl,
                "sections": [sect.title for sect in page.sections],
            }
            
            await self.storage.save_raw_data(data)
            await self.storage.save_processed_data(data)
            
            return data
        except Exception as e:
            print(f"Error accessing Wikipedia: {str(e)}")
            return None