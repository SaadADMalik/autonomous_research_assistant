"""
Test API responses for "careers for women" queries
"""
import asyncio
import sys
sys.path.append('d:\\autonomous_research_assistant')

from src.utils.arxiv_api import ArxivAPI
from src.utils.openalex_api import OpenAlexAPI
from src.utils.semantic_scholar_api import SemanticScholarAPI

async def test_apis():
    test_queries = [
        "best careers for women",
        "women career advancement",
        "female employment gender gap",
        "women in STEM"
    ]
    
    print("\n" + "="*80)
    print("TESTING OPENALEX API")
    print("="*80)
    
    openalex = OpenAlexAPI()
    for query in test_queries:
        print(f"\n>>> Query: '{query}'")
        print("-"*80)
        try:
            papers = await openalex.search(query, max_results=5)
            if papers:
                print(f"✅ Found {len(papers)} papers\n")
                for i, paper in enumerate(papers[:3], 1):
                    print(f"{i}. {paper['title'][:100]}")
                    print(f"   Year: {paper['year']}, Citations: {paper['citations']}")
                    print(f"   Venue: {paper.get('venue', 'Unknown')}")
            else:
                print("❌ No results returned - API may be filtering too aggressively")
        except Exception as e:
            print(f"❌ Error: {e}")
        await asyncio.sleep(0.2)
    
    await openalex.close()
    
    print("\n\n" + "="*80)
    print("TESTING SEMANTIC SCHOLAR API")
    print("="*80)
    
    sem_scholar = SemanticScholarAPI()
    for query in test_queries[:2]:  # Just test first 2 due to rate limits
        print(f"\n>>> Query: '{query}'")
        print("-"*80)
        try:
            papers = await sem_scholar.search(query, max_results=3)
            if papers:
                print(f"✅ Found {len(papers)} papers\n")
                for i, paper in enumerate(papers, 1):
                    print(f"{i}. {paper['title'][:100]}")
                    print(f"   Year: {paper.get('year', 'N/A')}, Citations: {paper.get('citations', 0)}")
            else:
                print("❌ No results returned")
        except Exception as e:
            print(f"❌ Error: {e}")
        await asyncio.sleep(2)
    
    await sem_scholar.close()

if __name__ == "__main__":
    asyncio.run(test_apis())
