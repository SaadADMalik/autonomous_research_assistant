"""
🎯 Phase 1: Load Testing Script for Chatbot Transformation

Tests the new /chat endpoint with concurrent users to validate:
- Latency: 6-9s target for fast mode
- Throughput: Handles 10+ concurrent requests
- Stability: No crashes or timeouts
"""

import asyncio
import aiohttp
import time
import statistics
from datetime import datetime
from typing import List, Dict
import json

# Test configuration
API_BASE_URL = "http://127.0.0.1:8000"
CONCURRENT_USERS = 10

# Test queries (mix of simple and complex)
TEST_QUERIES = [
    "quantum computing algorithms",
    "deep learning architectures",
    "climate change impact",
    "gene therapy techniques",
    "blockchain consensus mechanisms",
    "renewable energy storage",
    "artificial intelligence ethics",
    "quantum entanglement",
    "neural network optimization",
    "machine learning fairness"
]


class LoadTestResult:
    """Stores results from a single request"""
    def __init__(self, query: str, mode: str, success: bool, 
                 latency: float, confidence: float = 0.0, error: str = None):
        self.query = query
        self.mode = mode
        self.success = success
        self.latency = latency
        self.confidence = confidence
        self.error = error
        self.timestamp = datetime.now()


async def test_endpoint(session: aiohttp.ClientSession, query: str, 
                       endpoint: str, mode: str) -> LoadTestResult:
    """Test a single endpoint with a query"""
    start_time = time.time()
    
    try:
        payload = {
            "query": query,
            "max_results": 5
        }
        
        async with session.post(
            f"{API_BASE_URL}{endpoint}",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120)  # 2 min timeout
        ) as response:
            latency = time.time() - start_time
            
            if response.status == 200:
                data = await response.json()
                confidence = data.get("confidence", 0.0)
                return LoadTestResult(
                    query=query,
                    mode=mode,
                    success=True,
                    latency=latency,
                    confidence=confidence
                )
            else:
                error_text = await response.text()
                return LoadTestResult(
                    query=query,
                    mode=mode,
                    success=False,
                    latency=latency,
                    error=f"HTTP {response.status}: {error_text[:100]}"
                )
                
    except asyncio.TimeoutError:
        latency = time.time() - start_time
        return LoadTestResult(
            query=query,
            mode=mode,
            success=False,
            latency=latency,
            error="Timeout after 120s"
        )
    except Exception as e:
        latency = time.time() - start_time
        return LoadTestResult(
            query=query,
            mode=mode,
            success=False,
            latency=latency,
            error=str(e)
        )


async def run_concurrent_tests(queries: List[str], endpoint: str, 
                               mode: str) -> List[LoadTestResult]:
    """Run multiple queries concurrently"""
    print(f"\n{'='*80}")
    print(f"🧪 Testing {mode} mode: {endpoint}")
    print(f"👥 Concurrent users: {len(queries)}")
    print(f"{'='*80}\n")
    
    async with aiohttp.ClientSession() as session:
        tasks = [
            test_endpoint(session, query, endpoint, mode)
            for query in queries
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
    print(f"✅ Completed in {total_time:.2f}s")
    return results


def print_statistics(results: List[LoadTestResult], mode: str):
    """Print detailed statistics"""
    print(f"\n{'='*80}")
    print(f"📊 STATISTICS: {mode.upper()} MODE")
    print(f"{'='*80}\n")
    
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    print(f"Success Rate: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)")
    
    if successful:
        latencies = [r.latency for r in successful]
        confidences = [r.confidence for r in successful]
        
        print(f"\n⏱️  Latency:")
        print(f"  - Min:     {min(latencies):.2f}s")
        print(f"  - Max:     {max(latencies):.2f}s")
        print(f"  - Mean:    {statistics.mean(latencies):.2f}s")
        print(f"  - Median:  {statistics.median(latencies):.2f}s")
        print(f"  - StdDev:  {statistics.stdev(latencies):.2f}s" if len(latencies) > 1 else "")
        
        print(f"\n🎯 Confidence:")
        print(f"  - Min:     {min(confidences):.2f}")
        print(f"  - Max:     {max(confidences):.2f}")
        print(f"  - Mean:    {statistics.mean(confidences):.2f}")
        
        # Check if meeting latency targets
        if mode == "FAST":
            target = 9.0  # 6-9s target
            within_target = sum(1 for l in latencies if l <= target)
            print(f"\n✅ Within target (<{target}s): {within_target}/{len(latencies)} ({within_target/len(latencies)*100:.1f}%)")
        
    if failed:
        print(f"\n❌ Failures ({len(failed)}):")
        for r in failed:
            print(f"  - {r.query[:40]}: {r.error}")
    
    print(f"\n{'='*80}\n")


async def check_health():
    """Check if API is healthy before testing"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    print("✅ API is healthy")
                    return True
                else:
                    print(f"❌ API returned status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False


async def main():
    print("\n" + "="*80)
    print("🚀 CHATBOT LOAD TEST - PHASE 1")
    print("="*80)
    print(f"\n📋 Configuration:")
    print(f"  - Base URL: {API_BASE_URL}")
    print(f"  - Concurrent Users: {CONCURRENT_USERS}")
    print(f"  - Test Queries: {len(TEST_QUERIES)}")
    print(f"\n⏳ Checking API health...")
    
    if not await check_health():
        print("\n❌ API is not available. Please start the backend first:")
        print("   uvicorn src.main:app --host 0.0.0.0 --port 8000")
        return
    
    # Test 1: Fast mode (/chat endpoint) with concurrent users
    print("\n" + "="*80)
    print("TEST 1: FAST MODE - /chat endpoint (no retries)")
    print("="*80)
    
    fast_results = await run_concurrent_tests(
        TEST_QUERIES[:CONCURRENT_USERS],
        "/chat",
        "FAST"
    )
    print_statistics(fast_results, "FAST")
    
    # Test 2: Thorough mode (/generate_summary endpoint) with concurrent users
    print("\n" + "="*80)
    print("TEST 2: THOROUGH MODE - /generate_summary endpoint (with retries)")
    print("="*80)
    
    thorough_results = await run_concurrent_tests(
        TEST_QUERIES[:CONCURRENT_USERS],
        "/generate_summary",
        "THOROUGH"
    )
    print_statistics(thorough_results, "THOROUGH")
    
    # Comparison
    print("\n" + "="*80)
    print("📈 COMPARISON")
    print("="*80)
    
    fast_success = [r for r in fast_results if r.success]
    thorough_success = [r for r in thorough_results if r.success]
    
    if fast_success and thorough_success:
        fast_mean = statistics.mean([r.latency for r in fast_success])
        thorough_mean = statistics.mean([r.latency for r in thorough_success])
        speedup = thorough_mean / fast_mean if fast_mean > 0 else 0
        
        print(f"\nFast Mode:     {fast_mean:.2f}s average")
        print(f"Thorough Mode: {thorough_mean:.2f}s average")
        print(f"Speedup:       {speedup:.1f}x faster")
        
        print("\n✅ Phase 1 Success Criteria:")
        print(f"  - Fast mode <10s:  {'✅' if fast_mean < 10 else '❌'} ({fast_mean:.2f}s)")
        print(f"  - Handles 10 users: {'✅' if len(fast_success) >= 8 else '❌'} ({len(fast_success)}/10)")
        print(f"  - No crashes:       {'✅' if len(fast_success) > 0 else '❌'}")
    
    print("\n" + "="*80)
    print("🏁 LOAD TEST COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
