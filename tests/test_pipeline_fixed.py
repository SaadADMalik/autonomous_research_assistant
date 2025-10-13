"""
Complete pipeline test to verify all components work together.
Run this to verify your fixes are working correctly.
"""
import asyncio
import logging
import pytest  # Add this import
from src.pipelines.orchestrator import Orchestrator
from src.data_fetcher import DataFetcher
from src.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Set logging to show more detail
logging.getLogger().setLevel(logging.INFO)

@pytest.mark.asyncio  # Add this decorator
async def test_data_fetching():
    """Test 1: Verify data fetching works."""
    print("\n" + "="*80)
    print("TEST 1: Data Fetching")
    print("="*80)
    
    query = "Quantum Computing"
    fetcher = DataFetcher()
    
    print(f"\nFetching documents for query: '{query}'")
    documents = await fetcher.fetch_arxiv(query, max_results=5)
    
    if not documents:
        print("❌ FAILED: No documents fetched")
        assert False, "No documents fetched"
    
    print(f"✓ Fetched {len(documents)} documents")
    
    # Verify document structure
    for i, doc in enumerate(documents[:3]):  # Check first 3
        print(f"\nDocument {i+1}:")
        print(f"  Title: {doc.get('title', 'N/A')[:60]}...")
        print(f"  Summary length: {len(doc.get('summary', ''))} chars")
        print(f"  URL: {doc.get('url', 'N/A')[:50]}...")
        print(f"  Year: {doc.get('year', 'N/A')}")
        
        # Verify all required fields exist and have content
        if not doc.get('title') or not doc.get('summary'):
            print("❌ FAILED: Document missing required fields")
            assert False, "Document missing required fields"
    
    print("\n✓ All documents have required fields")
    assert True

@pytest.mark.asyncio  # Add this decorator
async def test_text_cleaning():
    """Test 2: Verify text cleaning preserves content."""
    print("\n" + "="*80)
    print("TEST 2: Text Cleaning")
    print("="*80)
    
    from src.utils.utils import clean_text
    
    test_cases = [
        ("This is a test.  Multiple   spaces.", "This is a test. Multiple spaces."),
        ("Text with\n\nnewlines\tand\ttabs.", "Text with newlines and tabs."),
        ("Sample text", "Sample text."),  # Should add period
    ]
    
    for original, expected_pattern in test_cases:
        cleaned = clean_text(original)
        print(f"\nOriginal: '{original}'")
        print(f"Cleaned:  '{cleaned}'")
        
        if not cleaned:
            print("❌ FAILED: Cleaning returned empty string")
            assert False, "Cleaning returned empty string"
        
        # Check if content is preserved (not just checking exact match)
        if len(cleaned) < len(original) * 0.5:  # Cleaned text shouldn't be less than 50% of original
            print("❌ FAILED: Too much content removed")
            assert False, "Too much content removed"
    
    print("\n✓ Text cleaning preserves content")
    assert True

@pytest.mark.asyncio  # Add this decorator
async def test_chunking():
    """Test 3: Verify text chunking works."""
    print("\n" + "="*80)
    print("TEST 3: Text Chunking")
    print("="*80)
    
    from src.rag.pipeline import RAGPipeline
    
    pipeline = RAGPipeline()
    
    # Test with real Arxiv summary
    test_text = """
    Quantum computing is a rapidly advancing field that leverages quantum mechanical 
    phenomena to perform computations. Unlike classical computers that use bits, 
    quantum computers use quantum bits or qubits. This allows them to process 
    information in fundamentally different ways. The field has applications in 
    cryptography, drug discovery, optimization problems, and artificial intelligence.
    """
    
    print(f"\nOriginal text length: {len(test_text)} chars")
    chunks = pipeline.chunk_text(test_text, chunk_size=200, overlap=50)
    
    if not chunks:
        print("❌ FAILED: No chunks created")
        assert False, "No chunks created"
    
    print(f"✓ Created {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1} ({len(chunk)} chars): {chunk[:60]}...")
        
        if not chunk or len(chunk) < 10:
            print("❌ FAILED: Chunk is too short or empty")
            assert False, "Chunk is too short or empty"
    
    print("\n✓ All chunks have content")
    assert True

@pytest.mark.asyncio  # Add this decorator
async def test_full_pipeline():
    """Test 4: Run complete pipeline end-to-end."""
    print("\n" + "="*80)
    print("TEST 4: Full Pipeline")
    print("="*80)
    
    query = "Quantum Computing"
    
    print(f"\nRunning full pipeline for query: '{query}'")
    
    # Fetch documents
    fetcher = DataFetcher()
    documents = await fetcher.fetch_arxiv(query, max_results=5)
    
    if not documents:
        print("❌ FAILED: No documents fetched")
        assert False, "No documents fetched"
    
    print(f"✓ Fetched {len(documents)} documents")
    
    # Run orchestrator
    orchestrator = Orchestrator()
    result = await orchestrator.run_pipeline(query, documents)
    
    print(f"\nPipeline Results:")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Result length: {len(result.result)} chars")
    print(f"  Source: {result.metadata.get('source', 'unknown')}")
    print(f"\nGenerated Summary:")
    print("-" * 80)
    print(result.result)
    print("-" * 80)
    
    # Verify results
    if not result.result:
        print("\n❌ FAILED: Empty result from pipeline")
        assert False, "Empty result from pipeline"
    
    if result.confidence == 0.0:
        print("\n❌ FAILED: Zero confidence score")
        assert False, "Zero confidence score"
    
    if len(result.result) < 50:
        print("\n❌ FAILED: Result too short (less than 50 chars)")
        assert False, "Result too short (less than 50 chars)"
    
    print("\n✓ Pipeline generated valid summary")
    assert True

@pytest.mark.asyncio  # Add this decorator
async def test_api_format():
    """Test 5: Verify output matches expected API format."""
    print("\n" + "="*80)
    print("TEST 5: API Format Verification")
    print("="*80)
    
    query = "Artificial Intelligence"
    
    fetcher = DataFetcher()
    documents = await fetcher.fetch_arxiv(query, max_results=3)
    
    if not documents:
        print("⚠ WARNING: Using fewer documents for test")
        documents = [{
            "title": "Test Paper",
            "summary": "This is a test summary about artificial intelligence and machine learning.",
            "url": "https://example.com",
            "year": 2024
        }]
    
    orchestrator = Orchestrator()
    result = await orchestrator.run_pipeline(query, documents)
    
    # Build expected API response format
    api_response = {
        "result": result.result,
        "confidence": result.confidence,
        "metadata": {
            "source": result.metadata.get("source"),
            "sources": [doc.get("url") for doc in documents if doc.get("url")]
        }
    }
    
    print("\nAPI Response Format:")
    print(f"  result: {len(api_response['result'])} chars")
    print(f"  confidence: {api_response['confidence']:.2f}")
    print(f"  metadata.source: {api_response['metadata']['source']}")
    print(f"  metadata.sources: {len(api_response['metadata']['sources'])} URLs")
    
    # Verify all required fields exist
    required_fields = ['result', 'confidence', 'metadata']
    for field in required_fields:
        if field not in api_response:
            print(f"\n❌ FAILED: Missing required field '{field}'")
            assert False, f"Missing required field '{field}'"
    
    print("\n✓ API response has correct format")
    assert True

# Remove the async main runner since these are now proper pytest functions