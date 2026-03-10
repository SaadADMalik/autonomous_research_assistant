"""
Test Enhanced Follow-Up Detection
Tests the exact scenario from user feedback:
1. Climate change → biodiversity (FOLLOW-UP ✅)
2. Biodiversity → animals (FOLLOW-UP ✅)  
3. Animals → species (FOLLOW-UP ✅)
4. "leave this" + AI in biotech (NEW TOPIC ✅)
5. AI/biotech → more AI/biotech (FOLLOW-UP ✅)
"""

import sys
sys.path.insert(0, '.')

from src.utils.conversation_manager import ConversationManager

def test_followup_detection():
    """Test enhanced follow-up detection with real scenarios"""
    
    manager = ConversationManager()
    session_id = "test_session_123"
    
    print("\n" + "="*80)
    print("🧪 TESTING ENHANCED FOLLOW-UP DETECTION")
    print("="*80)
    
    # Test 1: Initial query (should be NEW)
    query1 = "how does climate change affect biodiversity"
    is_followup = manager.is_follow_up(session_id, query1)
    print(f"\n1️⃣ Query: '{query1}'")
    print(f"   Result: {'🔄 FOLLOW-UP' if is_followup else '🆕 NEW TOPIC'}")
    print(f"   Expected: 🆕 NEW TOPIC")
    print(f"   Status: {'✅ PASS' if not is_followup else '❌ FAIL'}")
    
    # Add to history
    manager.add_turn(session_id, query1, "Climate change impacts biodiversity...", [], 0.85)
    
    # Test 2: Follow-up about animals (should be FOLLOW-UP)
    query2 = "and does climate change also affect animals?"
    is_followup = manager.is_follow_up(session_id, query2)
    print(f"\n2️⃣ Query: '{query2}'")
    print(f"   Result: {'🔄 FOLLOW-UP' if is_followup else '🆕 NEW TOPIC'}")
    print(f"   Expected: 🔄 FOLLOW-UP (same domain: climate)")
    print(f"   Status: {'✅ PASS' if is_followup else '❌ FAIL'}")
    
    # Add to history
    manager.add_turn(session_id, query2, "Animals are affected...", [], 0.80)
    
    # Test 3: Short follow-up (should be FOLLOW-UP)
    query3 = "which species is most affected by it"
    is_followup = manager.is_follow_up(session_id, query3)
    print(f"\n3️⃣ Query: '{query3}'")
    print(f"   Result: {'🔄 FOLLOW-UP' if is_followup else '🆕 NEW TOPIC'}")
    print(f"   Expected: 🔄 FOLLOW-UP (pronoun 'it' + climate keywords)")
    print(f"   Status: {'✅ PASS' if is_followup else '❌ FAIL'}")
    
    # Add to history
    manager.add_turn(session_id, query3, "Polar bears...", [], 0.82)
    
    # Test 4: CRITICAL - Topic shift with dismissal (should be NEW)
    query4 = "okay leave this and tell me one thing. How is AI advancing in biotech"
    is_followup = manager.is_follow_up(session_id, query4)
    print(f"\n4️⃣ Query: '{query4}'")
    print(f"   Result: {'🔄 FOLLOW-UP' if is_followup else '🆕 NEW TOPIC'}")
    print(f"   Expected: 🆕 NEW TOPIC (dismissal phrase + domain shift: climate → AI/biotech)")
    print(f"   Status: {'✅ PASS' if not is_followup else '❌ FAIL - HALLUCINATION RISK!'}")
    
    # Add to history
    manager.add_turn(session_id, query4, "AI in biotech...", [], 0.75)
    
    # Test 5: Follow-up in new domain (should be FOLLOW-UP)
    query5 = "what is the relation between ai climate and biotech?"
    is_followup = manager.is_follow_up(session_id, query5)
    print(f"\n5️⃣ Query: '{query5}'")
    print(f"   Result: {'🔄 FOLLOW-UP' if is_followup else '🆕 NEW TOPIC'}")
    print(f"   Expected: 🔄 FOLLOW-UP (AI + biotech keywords from previous)")
    print(f"   Status: {'✅ PASS' if is_followup else '❌ FAIL'}")
    
    # Test 6: Another dismissal phrase
    query6 = "forget about that, tell me about quantum computing"
    is_followup = manager.is_follow_up(session_id, query6)
    print(f"\n6️⃣ Query: '{query6}'")
    print(f"   Result: {'🔄 FOLLOW-UP' if is_followup else '🆕 NEW TOPIC'}")
    print(f"   Expected: 🆕 NEW TOPIC (dismissal phrase)")
    print(f"   Status: {'✅ PASS' if not is_followup else '❌ FAIL'}")
    
    # Test 7: Domain keyword test (AI → climate should be NEW)
    manager.add_turn(session_id, query6, "Quantum computing...", [], 0.80)
    query7 = "How does machine learning help with climate prediction"
    is_followup = manager.is_follow_up(session_id, query7)
    print(f"\n7️⃣ Query: '{query7}'")
    print(f"   Result: {'🔄 FOLLOW-UP' if is_followup else '🆕 NEW TOPIC'}")
    print(f"   Expected: 🆕 NEW TOPIC (domain overlap AI + climate, but quantum → ML+climate is shift)")
    print(f"   Expected Alternative: 🔄 FOLLOW-UP (if AI keywords match)")
    print(f"   Status: ℹ️  CONTEXT-DEPENDENT")
    
    print("\n" + "="*80)
    print("🎯 TEST SUMMARY")
    print("="*80)
    print("The most critical test is #4 (dismissal + domain shift)")
    print("If that passes, hallucinations from topic confusion will be prevented!")
    print("="*80 + "\n")


if __name__ == "__main__":
    test_followup_detection()
