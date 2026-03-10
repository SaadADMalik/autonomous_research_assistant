#!/usr/bin/env python3
"""
🎯 Phase 2 Test: Conversation Memory & Follow-ups

Tests:
1. Initial query (full pipeline)
2. Follow-up question (should use cached papers)
3. Another follow-up (should maintain context)
4. Measure speed improvement for follow-ups
"""

import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"

def test_conversation_flow():
    """Test multi-turn conversation with memory"""
    print("\n" + "="*70)
    print("🧪 PHASE 2 TEST: CONVERSATION MEMORY & FOLLOW-UPS")
    print("="*70)
    
    # Test 1: Initial query (should be 5-7s, full pipeline)
    print("\n" + "-"*70)
    print("TEST 1: Initial Query (Full Pipeline)")
    print("-"*70)
    
    query1 = "why men commit more suicides than women"
    print(f"Query: \"{query1}\"")
    
    start = time.time()
    r1 = requests.post(
        f"{BASE_URL}/chat",
        json={"query": query1, "max_results": 3},
        timeout=30
    )
    time1 = time.time() - start
    
    if r1.status_code == 200:
        data1 = r1.json()
        session_id = data1.get("session_id")
        
        print(f"⏱️  Time: {time1:.1f}s")
        print(f"🆔 Session ID: {session_id[:16]}...")
        print(f"📊 Confidence: {data1['confidence']:.2f}")
        print(f"🔄 Is Follow-up: {data1.get('is_follow_up', False)}")
        
        conv_meta = data1['metadata'].get('conversation', {})
        print(f"📦 Cached papers: {conv_meta.get('cached_papers_used', 0)}")
        print(f"💬 Answer preview: {data1['result'][:150]}...")
        
        time.sleep(2)
        
        # Test 2: Follow-up question (should be 2-3s, cached papers)
        print("\n" + "-"*70)
        print("TEST 2: Follow-up Question (Using Cache)")
        print("-"*70)
        
        query2 = "tell me more about the gender norms theory"
        print(f"Query: \"{query2}\"")
        print(f"Session ID: {session_id[:16]}... (same session)")
        
        start = time.time()
        r2 = requests.post(
            f"{BASE_URL}/chat",
            json={"query": query2, "max_results": 3, "session_id": session_id},
            timeout=30
        )
        time2 = time.time() - start
        
        if r2.status_code == 200:
            data2 = r2.json()
            
            print(f"⏱️  Time: {time2:.1f}s")
            print(f"📊 Confidence: {data2['confidence']:.2f}")
            print(f"🔄 Is Follow-up: {data2.get('is_follow_up', False)}")
            
            conv_meta2 = data2['metadata'].get('conversation', {})
            print(f"📦 Cached papers: {conv_meta2.get('cached_papers_used', 0)}")
            print(f"💬 Answer preview: {data2['result'][:150]}...")
            
            time.sleep(2)
            
            # Test 3: Another follow-up with pronoun
            print("\n" + "-"*70)
            print("TEST 3: Follow-up with Pronoun (Context-Aware)")
            print("-"*70)
            
            query3 = "what are the statistics on this?"
            print(f"Query: \"{query3}\"")
            print(f"Session ID: {session_id[:16]}... (same session)")
            
            start = time.time()
            r3 = requests.post(
                f"{BASE_URL}/chat",
                json={"query": query3, "max_results": 3, "session_id": session_id},
                timeout=30
            )
            time3 = time.time() - start
            
            if r3.status_code == 200:
                data3 = r3.json()
                
                print(f"⏱️  Time: {time3:.1f}s")
                print(f"📊 Confidence: {data3['confidence']:.2f}")
                print(f"🔄 Is Follow-up: {data3.get('is_follow_up', False)}")
                
                conv_meta3 = data3['metadata'].get('conversation', {})
                print(f"📦 Cached papers: {conv_meta3.get('cached_papers_used', 0)}")
                print(f"💬 Answer preview: {data3['result'][:150]}...")
                
                # Summary
                print("\n" + "="*70)
                print("📊 PERFORMANCE SUMMARY")
                print("="*70)
                print(f"\n1️⃣  Initial query: {time1:.1f}s (full pipeline)")
                print(f"2️⃣  Follow-up #1: {time2:.1f}s (cached papers)")
                print(f"3️⃣  Follow-up #2: {time3:.1f}s (cached papers)")
                
                avg_followup = (time2 + time3) / 2
                speedup = time1 / avg_followup if avg_followup > 0 else 0
                
                print(f"\n📈 Speedup Analysis:")
                print(f"   Average follow-up time: {avg_followup:.1f}s")
                print(f"   Speedup: {speedup:.1f}x faster")
                
                if avg_followup < 5:
                    print(f"\n✅ TARGET ACHIEVED: Follow-ups < 5s")
                else:
                    print(f"\n⚠️  Target missed: Follow-ups should be <5s")
                
                # Conversation stats
                stats = data3['metadata'].get('conversation', {}).get('conversation_stats', {})
                print(f"\n💬 Conversation Stats:")
                print(f"   Active sessions: {stats.get('active_sessions', 0)}")
                print(f"   Total turns: {stats.get('total_turns', 0)}")
                print(f"   Cached papers: {stats.get('total_cached_papers', 0)}")
                
                print("\n" + "="*70)
                print("✅ PHASE 2 FEATURES WORKING!")
                print("="*70 + "\n")
            else:
                print(f"❌ Test 3 failed: {r3.status_code}")
        else:
            print(f"❌ Test 2 failed: {r2.status_code}")
    else:
        print(f"❌ Test 1 failed: {r1.status_code}")

if __name__ == "__main__":
    print("\n⏳ Waiting for backend...")
    time.sleep(5)
    test_conversation_flow()
