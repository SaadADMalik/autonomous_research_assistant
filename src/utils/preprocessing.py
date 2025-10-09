import re
from typing import List
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

def chunk_text(text: str, max_length: int = 512) -> List[str]:
    """Split text into chunks of approximately equal size."""
    if not text:
        return []
    
    # Split by sentences to maintain context
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence_length = len(sentence)
        
        if current_length + sentence_length <= max_length:
            current_chunk.append(sentence)
            current_length += sentence_length
        else:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_length = sentence_length
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def create_metadata(source: str, query: str) -> dict:
    """Create standardized metadata for stored content."""
    return {
        "query": query,
        "source": source,
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "processed": True
    }