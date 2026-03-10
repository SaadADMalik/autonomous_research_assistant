"""
Comprehensive Test Suite: 50 Diverse Queries
Tests overall robustness and accuracy of the research assistant system.
"""
import asyncio
import json
import sys
import re
from datetime import datetime
sys.path.insert(0, 'src')

# Test queries covering diverse topics
TEST_QUERIES = [
    # Women & career queries (original problem area)
    "best careers for women",
    "women in technology leadership",
    "female CEO success factors",
    "gender pay gap in STEM",
    "work-life balance for working mothers",
    
    # Mental health & social issues
    "why men commit more suicides than women",
    "postpartum depression treatments",
    "teenage anxiety disorders",
    "PTSD in veterans",
    "social media impact on mental health",
    
    # Technology & CS
    "quantum computing applications",
    "machine learning in healthcare",
    "blockchain scalability solutions",
    "artificial intelligence ethics",
    "cybersecurity best practices",
    
    # Medicine & health
    "cancer immunotherapy breakthroughs",
    "diabetes prevention strategies",
    "Alzheimer's disease research",
    "COVID-19 vaccine effectiveness",
    "personalized medicine approaches",
    
    # Environment & climate
    "climate change mitigation strategies",
    "renewable energy technologies",
    "ocean acidification effects",
    "deforestation impact biodiversity",
    "carbon capture technologies",
    
    # Education & learning
    "online learning effectiveness",
    "STEM education for girls",
    "critical thinking skills development",
    "literacy rates developing countries",
    "educational technology innovations",
    
    # Economics & business
    "cryptocurrency market trends",
    "remote work productivity",
    "supply chain optimization",
    "startup funding strategies",
    "global economic inequality",
    
    # Physics & engineering
    "fusion energy breakthroughs",
    "nanotechnology applications",
    "robotics in manufacturing",
    "autonomous vehicle safety",
    "3D printing innovations",
    
    # Social sciences
    "urbanization impacts",
    "political polarization causes",
    "refugee crisis solutions",
    "income inequality trends",
    "education inequality",
    
    # Biology & genetics
    "CRISPR gene editing ethics",
    "microbiome health impacts",
    "aging research breakthroughs",
    "protein folding prediction",
    "synthetic biology applications"
]

async def test_all_queries():
    """Run all test queries and save detailed results."""
    
    results = []
    start_time = datetime.now()
    
    print(f"\n{'='*80}")
    print(f"COMPREHENSIVE SYSTEM TEST - {len(TEST_QUERIES)} queries")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    from data_fetcher import DataFetcher
    from agents.api_router_agent import APIRouterAgent
    
    fetcher = DataFetcher()
    router = APIRouterAgent()
    
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n[{i}/{len(TEST_QUERIES)}] Testing: '{query}'")
        print("-" * 80)
        
        try:
            # Get routing decision
            routing = router.route(query)
            
            # Fetch papers
            result = await fetcher.fetch_with_smart_routing(query, max_results=5)
            
            papers = result['papers']
            apis_used = result['apis_used']
            
            # Check for problematic content
            summary_text = " ".join([(p.get('summary') or '')[:200] for p in papers])
            has_contamination = bool(re.search(r'\b(rape|rapist|convicted|prison|inmate)\b', summary_text, re.IGNORECASE))
            
            # Check for table-of-contents style text (many colons)
            has_toc = summary_text.count(':') / max(len(summary_text), 1) * 100 > 3
            
            # Analyze source quality
            sources = {}
            for paper in papers:
                source = paper.get('source', 'unknown')
                sources[source] = sources.get(source, 0) + 1
            
            test_result = {
                "query": query,
                "routing": {
                    "primary_api": routing['primary'],
                    "domain": routing['domain'],
                    "confidence": routing['confidence']
                },
                "results": {
                    "paper_count": len(papers),
                    "apis_used": apis_used,
                    "sources": sources
                },
                "quality_checks": {
                    "has_contamination": has_contamination,
                    "has_table_of_contents": has_toc,
                    "uses_educational_fallback": 'educational_fallback' in apis_used
                },
                "papers": [
                    {
                        "title": p.get('title', 'Unknown')[:100],
                        "source": p.get('source', 'unknown'),
                        "year": p.get('year', 'N/A'),
                        "citations": p.get('citations', 0)
                    }
                    for p in papers[:3]
                ]
            }
            
            results.append(test_result)
            
            # Print summary
            status = "✅" if not has_contamination and len(papers) > 0 else "⚠️"
            print(f"{status} Papers: {len(papers)}, APIs: {', '.join(apis_used)}")
            if has_contamination:
                print(f"  ⚠️  WARNING: Possible contamination detected")
            if has_toc:
                print(f"  ⚠️  WARNING: Table-of-contents style text detected")
            
            # Rate limiting
            await asyncio.sleep(0.3)
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            results.append({
                "query": query,
                "error": str(e),
                "quality_checks": {"has_error": True}
            })
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Save results
    output = {
        "test_metadata": {
            "total_queries": len(TEST_QUERIES),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration
        },
        "results": results
    }
    
    filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Generate summary
    print(f"\n\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total queries: {len(results)}")
    print(f"Duration: {duration:.1f}s ({duration/len(results):.1f}s per query)")
    
    contaminated = sum(1 for r in results if r.get('quality_checks', {}).get('has_contamination', False))
    has_toc_count = sum(1 for r in results if r.get('quality_checks', {}).get('has_table_of_contents', False))
    fallback_count = sum(1 for r in results if r.get('quality_checks', {}).get('uses_educational_fallback', False))
    error_count = sum(1 for r in results if 'error' in r)
    
    print(f"\nQuality Metrics:")
    print(f"  Clean results: {len(results) - contaminated - error_count} ({(len(results)-contaminated-error_count)/len(results)*100:.1f}%)")
    print(f"  Contaminated: {contaminated} (" + (f"{contaminated/len(results)*100:.1f}%" if contaminated > 0 else "0.0%") + ")")
    print(f"  Table-of-contents style: {has_toc_count}")
    print(f"  Educational fallback: {fallback_count}")
    print(f"  Errors: {error_count}")
    
    print(f"\nFull results saved to: {filename}")
    print(f"{'='*80}\n")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_all_queries())
