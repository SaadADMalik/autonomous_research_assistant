import json
import os
from datetime import datetime, UTC
from typing import Dict, Any
from pathlib import Path

class DataStorage:
    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"
        self._init_directories()

    def _init_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, source: str, query: str) -> str:
        """Generate a unique filename for the data."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_query = safe_query[:50]  # Limit filename length
        return f"{source}_{safe_query}_{timestamp}.json"

    async def save_raw_data(self, data: Dict[str, Any]) -> str:
        """Save raw API response data."""
        filename = self._generate_filename(data['source'], data['query'])
        filepath = self.raw_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(filepath)

    async def save_processed_data(self, data: Dict[str, Any]) -> str:
        """Save processed data."""
        filename = self._generate_filename(data['source'], data['query'])
        filepath = self.processed_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(filepath)

    async def load_data(self, filepath: str) -> Dict[str, Any]:
        """Load data from a file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)