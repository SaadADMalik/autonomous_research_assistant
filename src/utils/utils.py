"""
Utility functions for text processing and data handling.
"""
import re
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """
    Clean text while preserving important content and structure.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text with preserved punctuation and structure
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Remove HTML tags if present
    text = re.sub(r'<[^>]+>', '', text)
    
    # Replace multiple whitespaces (tabs, newlines, spaces) with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters but keep printable ones
    text = ''.join(char for char in text if char.isprintable() or char.isspace())
    
    # Remove multiple periods (e.g., "..." -> ".")
    text = re.sub(r'\.{2,}', '.', text)
    
    # Remove multiple commas
    text = re.sub(r',{2,}', ',', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    # Ensure text ends with proper punctuation if it doesn't
    if text and text[-1] not in '.!?':
        text += '.'
    
    return text


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """
    Split text into overlapping chunks for processing.
    
    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text or len(text) < 10:
        logger.warning(f"Text too short for chunking: {len(text)} characters")
        return []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # If not the last chunk, try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings near the chunk boundary
            sentence_end = text.rfind('.', start, end)
            if sentence_end > start + chunk_size // 2:  # Only if we find one reasonably far in
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap if end < len(text) else end
    
    return chunks


def create_metadata(source: str, query: str, **kwargs) -> dict:
    """
    Create metadata dictionary for stored documents.
    
    Args:
        source: Source of the data (e.g., 'arxiv', 'wikipedia')
        query: Original search query
        **kwargs: Additional metadata fields
        
    Returns:
        Metadata dictionary
    """
    metadata = {
        "source": source,
        "query": query,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processed": True
    }
    metadata.update(kwargs)
    return metadata


def validate_url(url: str) -> bool:
    """
    Validate if a string is a proper URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    Truncate text to specified length, ending at word boundary.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    # Find the last space before max_length
    truncated = text[:max_length].rsplit(' ', 1)[0]
    return truncated + suffix


def extract_year_from_date(date_string: str) -> int:
    """
    Extract year from various date string formats.
    
    Args:
        date_string: Date string (e.g., "2024-01-15", "2024")
        
    Returns:
        Year as integer, or current year if parsing fails
    """
    try:
        # Try different date formats
        for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%SZ', '%Y']:
            try:
                return datetime.strptime(date_string[:10] if len(date_string) > 4 else date_string, fmt).year
            except ValueError:
                continue
        
        # If all formats fail, try to extract first 4 digits
        year_match = re.search(r'\d{4}', date_string)
        if year_match:
            return int(year_match.group())
        
    except Exception as e:
        logger.warning(f"Failed to extract year from '{date_string}': {e}")
    
    # Return current year as fallback
    return datetime.now(timezone.utc).year


def format_confidence_score(confidence: float) -> str:
    """
    Format confidence score as percentage string.
    
    Args:
        confidence: Confidence score (0-1)
        
    Returns:
        Formatted percentage string (e.g., "85.5%")
    """
    return f"{confidence * 100:.1f}%"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove invalid filename characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    # Limit length
    sanitized = sanitized[:200]
    return sanitized