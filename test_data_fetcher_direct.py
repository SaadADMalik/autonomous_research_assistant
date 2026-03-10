"""
Test the data fetcher's smart routing directly
"""
import asyncio
import sys
sys.path.append('d:\\autonomous_research_assistant')

from src.data_fetcher import DataFetcher

async def test_data_fetcher():
    print("Initializing DataFetcher...")
    fetcher = DataFetcher()
    
    print("\nTesting fetch_with_smart_routing for 'quantum computing'...")
    try:
        result = await fetcher.fetch_with_smart_routing("quantum computing", max_results=15)
        
        print(f"\n✅ SUCCESS!")
        print(f"   Papers: {result['total_papers']}")
        print(f"   APIs Used: {result['apis_used']}")
        print(f"   Routing: {result['routing_info']['primary']} ({result['routing_info']['domain']})")
        print(f"   Fetch Times: {result['fetch_times']}")
        
        if result['papers']:
            print(f"\n   First paper: {result['papers'][0].get('title', 'NO TITLE')}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_data_fetcher())
