import asyncio
import logging
from src.utils.semantic_scholar_api import SemanticScholarAPI
from src.data_fetcher import DataFetcher

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_semantic_scholar_direct():
    """Test Semantic Scholar API directly."""
    print("\n" + "="*80)
    print("TESTING SEMANTIC SCHOLAR API DIRECTLY")
    print("="*80)
    
    api = SemanticScholarAPI()
    
    test_queries = [
        "quantum computing",
        "diabetes treatment", 
        "artificial intelligence",
        "climate change"
    ]
    
    for query in test_queries:
        print(f"\n--- Testing query: '{query}' ---")
        results = await api.search(query, 3)
        
        if results:
            print(f"✅ SUCCESS: Found {len(results)} papers")
            for i, paper in enumerate(results[:2], 1):
                print(f"  {i}. {paper['title'][:60]}...")
                print(f"     Authors: {', '.join(paper['authors'][:2])}...")
                print(f"     Year: {paper['year']}")
                print(f"     Citations: {paper.get('citations', 0)}")
                print(f"     URL: {paper['url'][:50]}...")
        else:
            print(f"❌ FAILED: No results for '{query}'")

async def test_data_fetcher():
    """Test DataFetcher with new implementation."""
    print("\n" + "="*80)
    print("TESTING DATA FETCHER (Semantic Scholar + ArXiv backup)")
    print("="*80)
    
    fetcher = DataFetcher()
    
    test_queries = [
        "machine learning",
        "cancer research"
    ]
    
    for query in test_queries:
        print(f"\n--- Testing DataFetcher with: '{query}' ---")
        results = await fetcher.fetch_arxiv(query, 3)
        
        if results:
            print(f"✅ SUCCESS: Found {len(results)} papers")
            
            # Check which API was used
            sources = [paper.get('source', paper.get('categories', ['unknown'])[0]) for paper in results]
            print(f"Sources used: {set(sources)}")
            
            for i, paper in enumerate(results[:2], 1):
                print(f"  {i}. {paper['title'][:60]}...")
                print(f"     Source: {paper.get('source', 'unknown')}")
        else:
            print(f"❌ FAILED: No results for '{query}'")

async def test_full_pipeline():
    """Test the complete pipeline."""
    print("\n" + "="*80)
    print("TESTING FULL PIPELINE")
    print("="*80)
    
    from src.pipelines.orchestrator import Orchestrator
    
    fetcher = DataFetcher()
    orchestrator = Orchestrator()
    
    query = "artificial intelligence"
    print(f"\nTesting full pipeline with: '{query}'")
    
    # Fetch documents
    documents = await fetcher.fetch_all(query, 3)
    print(f"Fetched {len(documents)} documents")
    
    if documents:
        # Run pipeline
        result = await orchestrator.run_pipeline(query, documents)
        print(f"\nPipeline Results:")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Result length: {len(result.result)} chars")
        print(f"  Summary preview: {result.result[:100]}...")
    else:
        print("❌ No documents to process")

async def main():
    """Run all tests."""
    print("🧪 TESTING SEMANTIC SCHOLAR INTEGRATION")
    print("=" * 80)
    
    try:
        await test_semantic_scholar_direct()
        await test_data_fetcher() 
        await test_full_pipeline()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80)
        print("\nIf Semantic Scholar is working well, we can remove ArXiv in Phase 3!")
        
    except Exception as e:
        print(f"\n❌ ERROR during testing: {str(e)}")
        logger.error("Test failed", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())