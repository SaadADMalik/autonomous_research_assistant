import pytest
from datetime import datetime, UTC
import os
from src.utils.preprocessing import clean_text, chunk_text, create_metadata
from src.utils.wikipedia_utils import WikipediaAPI
from src.utils.arxiv_utils import ArxivAPI
from src.utils.storage import DataStorage

# Preprocessing tests
def test_clean_text():
    text = "This   is  a   test   text  with    spaces  and $pecial ch@racters!"
    cleaned = clean_text(text)
    assert cleaned == "This is a test text with spaces and pecial chracters!"
    assert "  " not in cleaned

def test_chunk_text():
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    chunks = chunk_text(text, max_length=20)
    assert len(chunks) > 1
    assert all(len(chunk) <= 20 for chunk in chunks)

def test_create_metadata():
    metadata = create_metadata("test_source", "test_query")
    assert "query" in metadata
    assert "source" in metadata
    assert "timestamp" in metadata
    assert "processed" in metadata

# API tests
@pytest.mark.asyncio
async def test_wikipedia_api():
    wiki = WikipediaAPI()
    result = await wiki.search("Python programming language")
    assert result is not None
    assert "content" in result
    assert len(result["content"]) > 0
    assert "title" in result
    assert "url" in result

@pytest.mark.asyncio
async def test_arxiv_api():
    arxiv_api = ArxivAPI()
    results = await arxiv_api.search("quantum computing", max_results=2)
    assert len(results) > 0
    assert "title" in results[0]
    assert "summary" in results[0]
    assert "authors" in results[0]
    assert len(results) <= 2

@pytest.mark.asyncio
async def test_data_storage():
    # Initialize storage
    storage = DataStorage("data")
    
    # Test data
    test_data = {
        "query": "test query",
        "source": "test_source",
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "content": "test content"
    }
    
    # Test saving raw data
    raw_filepath = await storage.save_raw_data(test_data)
    assert os.path.exists(raw_filepath)
    
    # Test saving processed data
    processed_filepath = await storage.save_processed_data(test_data)
    assert os.path.exists(processed_filepath)
    
    # Test loading data
    loaded_data = await storage.load_data(processed_filepath)
    assert loaded_data["query"] == test_data["query"]
    assert loaded_data["content"] == test_data["content"]

    # Clean up test files
    os.remove(raw_filepath)
    os.remove(processed_filepath)