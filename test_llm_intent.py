"""
Test LLM-based Intent Analysis and Smart Cache Filtering

Tests the exact user scenario that caused hallucinations:
1. Asking about different topics in sequence
2. Checking if cache is properly filtered by relevance
3. Ensuring no cross-topic contamination
"""
import requests
import json
import time

API_URL = "http://localhost:8000/chat"

def make_query(query, session_id=None):
    """Make a query and return response with timing."""
    payload = {"query": query}
    if session_id:
        payload["session_id"] = session_id
    
    start = time.time()
    response = requests.post(API_URL, json=payload)
    elapsed = time.time() - start
    
    if response.status_code != 200:
        print(f"❌ ERROR: {response.status_code}")
        print(response.text)
        return None, None, elapsed
    
    data = response.json()
    return data.get("result"), data.get("session_id"), elapsed


def test_user_scenario():
    """Test exact user scenario from conversation log."""
    print("=" * 80)
    print("🧪 TESTING LLM-BASED INTENT ANALYSIS & SMART CACHE FILTERING")
    print("=" * 80)
    print()
    
    session_id = None
    
    # Query 1: Climate topic
    print("1️⃣  Query: 'why older generation is better'")
    result, session_id, elapsed = make_query("why older generation is better", session_id)
    if result:
        print(f"   ✅ Response ({elapsed:.1f}s): {result[:150]}...")
        print()
    
    time.sleep(1)
    
    # Query 2: Follow-up on climate
    print("2️⃣  Query: 'then why does my parent say their generation was better'")
    result, session_id, elapsed = make_query("then why does my parent say their generation was better", session_id)
    if result:
        print(f"   ✅ Response ({elapsed:.1f}s - should be fast ~2s): {result[:150]}...")
        print()
    
    time.sleep(1)
    
    # Query 3: Follow-up with pronoun
    print("3️⃣  Query: 'so am i better generation than my parents??'")
    result, session_id, elapsed = make_query("so am i better generation than my parents??", session_id)
    if result:
        print(f"   ✅ Response ({elapsed:.1f}s - should be fast ~2s): {result[:150]}...")
        print()
    
    time.sleep(1)
    
    # Query 4: Tech angle
    print("4️⃣  Query: 'no, i get you but in terms like we are sharp with tech and my parents arent'")
    result, session_id, elapsed = make_query("no, i get you but in terms like we are sharp with tech and my parents arent", session_id)
    if result:
        print(f"   ✅ Response ({elapsed:.1f}s): {result[:150]}...")
        print()
    
    time.sleep(1)
    
    # Query 5: CRITICAL - Topic shift with dismissal phrase
    print("5️⃣  Query: 'okay leave it and tell me what is the role of machine learning in biotech these days'")
    print("   🎯 CRITICAL: Should detect dismissal + topic shift (climate→biotech)")
    print("   🎯 Expected: Fetch NEW biotech papers (not reuse climate papers)")
    result, session_id, elapsed = make_query("okay leave it and tell me what is the role of machine learning in biotech these days", session_id)
    if result:
        has_climate_terms = any(term in result.lower() for term in ["climate", "temperature", "biodiversity", "species", "e-book", "student"])
        has_biotech_terms = any(term in result.lower() for term in ["biotech", "machine learning", "genetic", "medicine", "drug", "gene"])
        
        print(f"   ✅ Response ({elapsed:.1f}s): {result[:200]}...")
        print(f"   📊 Contains climate terms: {'❌ YES (HALLUCINATION!)' if has_climate_terms else '✅ NO'}")
        print(f"   📊 Contains biotech terms: {'✅ YES' if has_biotech_terms else '❌ NO (WRONG PAPERS!)'}")
        print()
    
    time.sleep(1)
    
    # Query 6: Follow-up on biotech
    print("6️⃣  Query: 'is it possible to clone human using ai'")
    print("   🎯 Should be follow-up, but check if it uses only biotech papers (not climate)")
    result, session_id, elapsed = make_query("is it possible to clone human using ai", session_id)
    if result:
        has_climate_terms = any(term in result.lower() for term in ["climate", "temperature", "biodiversity", "e-book", "student"])
        has_biotech_terms = any(term in result.lower() for term in ["biotech", "cloning", "genetic", "ai", "machine learning"])
        
        print(f"   ✅ Response ({elapsed:.1f}s - should be fast ~2s): {result[:200]}...")
        print(f"   📊 Contains climate terms: {'❌ YES (HALLUCINATION!)' if has_climate_terms else '✅ NO'}")
        print(f"   📊 Contains biotech/AI terms: {'✅ YES' if has_biotech_terms else '❌ NO'}")
        print()
    
    time.sleep(1)
    
    # Query 7: Another dismissal + new topic
    print("7️⃣  Query: 'leave that and answer me once. Is it possible to clone humans using AI now?'")
    print("   🎯 Should detect dismissal phrase, may still be biotech topic")
    result, session_id, elapsed = make_query("leave that and answer me once. Is it possible to clone humans using AI now?", session_id)
    if result:
        print(f"   ✅ Response ({elapsed:.1f}s): {result[:200]}...")
        print()
    
    time.sleep(1)
    
    # Query 8: New biology angle
    print("8️⃣  Query: 'I've heard humans have cloned sheep? is it true? in which year?'")
    result, session_id, elapsed = make_query("I've heard humans have cloned sheep? is it true? in which year?", session_id)
    if result:
        has_dolly = "dolly" in result.lower()
        has_1996 = "1996" in result or "1997" in result
        print(f"   ✅ Response ({elapsed:.1f}s): {result[:200]}...")
        print(f"   📊 Mentions Dolly: {'✅ YES' if has_dolly else '❌ NO'}")
        print(f"   📊 Mentions 1996: {'✅ YES' if has_1996 else '❌ NO'}")
        print()
    
    time.sleep(1)
    
    # Query 9: Follow-up
    print("9️⃣  Query: 'so if sheeps can be cloned then why not other animals?'")
    result, session_id, elapsed = make_query("so if sheeps can be cloned then why not other animals?", session_id)
    if result:
        print(f"   ✅ Response ({elapsed:.1f}s - should be fast ~2s): {result[:200]}...")
        print()
    
    time.sleep(1)
    
    # Query 10: CRITICAL - Context-dependent query
    print("🔟 Query: 'im not asking about humans now, im asking about other animals like lion, cat, dog'")
    print("   🎯 CRITICAL: In cloning context, should search 'cloning animals' NOT 'animal philosophy'")
    result, session_id, elapsed = make_query("im not asking about humans now, im asking about other animals like lion, cat, dog", session_id)
    if result:
        has_philosophy = any(term in result.lower() for term in ["philosophy", "cause-and-effect", "inductive reasoning", "william whewell"])
        has_cloning = any(term in result.lower() for term in ["clon", "genetic", "somatic", "dna", "biotech"])
        
        print(f"   ✅ Response ({elapsed:.1f}s): {result[:200]}...")
        print(f"   📊 Contains philosophy terms: {'❌ YES (WRONG PAPERS!)' if has_philosophy else '✅ NO'}")
        print(f"   📊 Contains cloning terms: {'✅ YES' if has_cloning else '❌ NO (MISSED CONTEXT!)'}")
        print()
    
    print("=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_user_scenario()
