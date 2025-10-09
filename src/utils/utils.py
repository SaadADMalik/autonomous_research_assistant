def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and special characters.
    """
    if not isinstance(text, str):
        return ""
    text = text.strip()
    text = ' '.join(text.split())  # Normalize whitespace
    return text

def chunk_text(text: str, max_length: int = 500) -> list[str]:
    """
    Split text into chunks of max_length characters.
    """
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