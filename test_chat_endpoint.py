"""
🎯 Phase 1: Quick test of the new /chat endpoint
Tests that fast mode works and is faster than thorough mode.
"""

import requests
import time
import json

API_BASE_URL = "http://127.0.0.1:8000"
TEST_QUERY = "quantum computing algorithms"

def test_endpoint(endpoint: str, mode_name: str):
    """Test a single endpoint and print results"""
    print(f"\n{'='*60}")
    print(f"Testing {mode_name}: {endpoint}")
    print(f"{'='*60}")
    
    payload = {
        "query": TEST_QUERY,
        "max_results": 5
    }
    
    print(f"Query: '{TEST_QUERY}'")
    print(f"⏳ Sending request...")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_BASE_URL}{endpoint}",
            json=payload,
            timeout=120
        )
        
        latency = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            confidence = data.get("confidence", 0.0)
            metadata = data.get("metadata", {})
            performance = metadata.get("performance", {})
            
            print(f"✅ SUCCESS")
            print(f"\n⏱️  Latency: {latency:.2f}s")
            print(f"🎯 Confidence: {confidence:.2f}")
            print(f"📊 Mode: {performance.get('mode', 'unknown')}")
            print(f"🔄 Attempts: {performance.get('max_attempts', 'unknown')}")
            
            if 'breakdown' in performance:
                print(f"\n📈 Performance Breakdown:")
                for key, value in performance['breakdown'].items():
                    print(f"  - {key}: {value}s")
            
            # Show summary preview
            summary = data.get("result", "")
            print(f"\n📝 Summary (first 200 chars):")
            print(f"   {summary[:200]}...")
            
            return latency, confidence
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(response.text[:500])
            return None, None
            
    except requests.Timeout:
        print(f"❌ TIMEOUT after 120s")
        return None, None
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None, None


def main():
    print("\n" + "="*60)
    print("🚀 CHATBOT ENDPOINT TEST - PHASE 1")
    print("="*60)
    
    # Check health
    print("\n⏳ Checking API health...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is healthy")
        else:
            print(f"❌ API returned status {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("\nPlease start the backend first:")
        print("  uvicorn src.main:app --host 0.0.0.0 --port 8000")
        return
    
    # Test fast mode
    fast_latency, fast_confidence = test_endpoint("/chat", "FAST MODE (new)")
    
    # Test thorough mode
    thorough_latency, thorough_confidence = test_endpoint("/generate_summary", "THOROUGH MODE (old)")
    
    # Comparison
    if fast_latency and thorough_latency:
        print(f"\n{'='*60}")
        print("📊 COMPARISON")
        print(f"{'='*60}")
        print(f"\nFast Mode:     {fast_latency:.2f}s")
        print(f"Thorough Mode: {thorough_latency:.2f}s")
        speedup = thorough_latency / fast_latency
        print(f"Speedup:       {speedup:.1f}x faster")
        
        print(f"\n✅ Phase 1 Target: <10s for fast mode")
        if fast_latency < 10:
            print(f"   ✅ PASSED ({fast_latency:.2f}s < 10s)")
        else:
            print(f"   ❌ FAILED ({fast_latency:.2f}s >= 10s)")
    
    print(f"\n{'='*60}")
    print("🏁 TEST COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
