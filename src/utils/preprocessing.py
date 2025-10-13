import re
from typing import List  # Fixed: was "from typing: List"
from datetime import datetime, UTC

def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    
    return text

def chunk_text(text: str, max_length: int = 500) -> List[str]:
    """Split text into chunks of max_length characters."""
    if not text:
        return []
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + 1  # Account for space
        if current_length + word_length > max_length:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

def create_metadata(source: str, query: str) -> dict:
    """Create standardized metadata for stored content."""
    return {
        "query": query,
        "source": source,
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "processed": True
    }