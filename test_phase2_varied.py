"""
Phase 2 Varied Test - Multiple topics with follow-ups
"""
import requests
import time
import json

BASE_URL = "http://localhost:8000"

def wait_for_backend():
    for _ in range(10):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=3)
            if r.status_code == 200:
                return True
        except:
            time.sleep(1)
    return False

def ask(query, session_id=None, label=""):
    payload = {"query": query, "max_results": 5}
    if session_id:
        payload["session_id"] = session_id

    start = time.time()
    try:
        r = requests.post(f"{BASE_URL}/chat", json=payload, timeout=30)
        elapsed = time.time() - start
        if r.status_code == 200:
            data = r.json()
            conv = data["metadata"].get("conversation", {})
            return {
                "ok": True,
                "time": elapsed,
                "session_id": data.get("session_id"),
                "is_follow_up": data.get("is_follow_up", False),
                "cached_papers": conv.get("cached_papers_used", 0),
                "confidence": data.get("confidence", 0),
                "answer": data.get("result", "")[:200],
            }
        else:
            return {"ok": False, "status": r.status_code, "time": elapsed}
    except Exception as e:
        return {"ok": False, "error": str(e), "time": time.time() - start}

def print_result(label, q, res):
    status = "✅" if res["ok"] else "❌"
    follow_up_tag = " [FOLLOW-UP]" if res.get("is_follow_up") else " [NEW]"
    cached_tag = f" 📦{res['cached_papers']} cached" if res.get("cached_papers", 0) > 0 else ""
    print(f"\n  {status} {label}{follow_up_tag}{cached_tag}")
    print(f"     Query   : \"{q}\"")
    if res["ok"]:
        print(f"     Time    : {res['time']:.1f}s")
        print(f"     Confidence: {res['confidence']:.2f}")
        print(f"     Answer  : {res['answer'][:150]}...")
    else:
        print(f"     Error   : {res.get('error') or res.get('status')}")

def run_conversation(title, turns):
    """Run a multi-turn conversation"""
    print(f"\n{'='*70}")
    print(f"  TOPIC: {title}")
    print(f"{'='*70}")
    
    session_id = None
    times = []
    initial_time = None
    
    for i, (label, query) in enumerate(turns):
        res = ask(query, session_id)
        print_result(label, query, res)
        
        if res["ok"]:
            if session_id is None:
                session_id = res["session_id"]
                initial_time = res["time"]
            times.append(res["time"])
    
    if len(times) > 1 and initial_time:
        follow_up_avg = sum(times[1:]) / len(times[1:])
        speedup = initial_time / follow_up_avg if follow_up_avg > 0 else 0
        print(f"\n  📊 Initial: {initial_time:.1f}s  |  Follow-ups avg: {follow_up_avg:.1f}s  |  Speedup: {speedup:.1f}x")
    
    return times

print("\n" + "="*70)
print("  PHASE 2 TEST: MULTI-TURN CONVERSATIONS (VARIED TOPICS)")
print("="*70)

if not wait_for_backend():
    print("❌ Backend not responding!")
    exit(1)

print("✅ Backend ready\n")

# ─── Conversation 1: Mental Health ───────────────────────────────────────────
t1 = run_conversation("MENTAL HEALTH", [
    ("Turn 1 (initial)", "why do teenagers experience depression more than adults"),
    ("Turn 2 (follow-up phrase)", "tell me more about social media's role"),
    ("Turn 3 (pronoun)", "what are the statistics on this?"),
])

# ─── Conversation 2: Climate Science ─────────────────────────────────────────
t2 = run_conversation("CLIMATE SCIENCE", [
    ("Turn 1 (initial)", "how does climate change affect biodiversity"),
    ("Turn 2 (follow-up phrase)", "explain the coral reef impact more"),
    ("Turn 3 (pronoun + what about)", "what about ocean acidification?"),
])

# ─── Conversation 3: Gender & Society ────────────────────────────────────────
t3 = run_conversation("GENDER & SOCIETY", [
    ("Turn 1 (initial)", "why is there a gender pay gap in tech"),
    ("Turn 2 (pronoun)", "how did that start historically?"),
    ("Turn 3 (follow-up phrase)", "what else contributes to this problem"),
])

# ─── Conversation 4: Neuroscience ────────────────────────────────────────────
t4 = run_conversation("NEUROSCIENCE", [
    ("Turn 1 (initial)", "how does sleep deprivation affect brain function"),
    ("Turn 2 (tell me more)", "tell me more about memory consolidation"),
    ("Turn 3 (short pronoun)", "is it reversible?"),
])

# ─── SUMMARY ─────────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("  OVERALL SUMMARY")
print(f"{'='*70}")

all_times = t1 + t2 + t3 + t4
initial_times = [t1[0], t2[0], t3[0], t4[0]]
follow_up_times = t1[1:] + t2[1:] + t3[1:] + t4[1:]

if initial_times and follow_up_times:
    avg_initial = sum(initial_times) / len(initial_times)
    avg_followup = sum(follow_up_times) / len(follow_up_times)
    speedup = avg_initial / avg_followup if avg_followup > 0 else 0
    print(f"\n  Avg initial query  : {avg_initial:.1f}s")
    print(f"  Avg follow-up      : {avg_followup:.1f}s")
    print(f"  Overall speedup    : {speedup:.1f}x")
    print(f"  Follow-ups < 5s    : {'✅ YES' if avg_followup < 5 else '❌ NO'}")
    print(f"  Sessions tested    : 4")
    print(f"  Total turns        : {len(all_times)}")

print(f"\n{'='*70}\n")
