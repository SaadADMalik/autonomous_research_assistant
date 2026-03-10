# Race-Condition API Design for Conversational Chatbot

## 🎯 User's Vision
- Ask questions like "why men are more prone to suicides"
- System searches all APIs simultaneously (race condition)
- Show fastest response first
- Can challenge false statements with research citations
- **MUST BE FREE**

## ✅ Current State (Already Free!)
- **Groq API**: FREE tier (30 req/min, $0/month)
- **SemanticScholar**: FREE (no limits for reasonable use)
- **Wikipedia**: FREE (no API key needed)
- **ArXiv**: FREE
- **OpenAlex**: FREE
- **Total cost**: $0 ✅

## 🏗️ Architecture Options

### Option 1: Pure Race (Fastest Wins)
```python
# Launch all APIs, return whoever responds first
tasks = [fetch_wikipedia(query), fetch_semantic_scholar(query), 
         fetch_arxiv(query), fetch_openalex(query)]
done, pending = await asyncio.wait(tasks, return_when=FIRST_COMPLETED)
# Use first result, cancel others
for task in pending:
    task.cancel()
```

**Pros:**
- Ultra-fast (2-3s, Wikipedia usually wins)
- Simple logic

**Cons:**
- Wikipedia always wins (fastest but not always best)
- Wastes other API calls
- Might miss high-quality papers

### Option 2: Timeout Window (Our Recommendation ✅)
```python
# Launch all APIs, use whoever responds within 5s
tasks = [fetch_wikipedia(query), fetch_semantic_scholar(query), 
         fetch_arxiv(query), fetch_openalex(query)]
done, pending = await asyncio.wait(tasks, timeout=5.0, return_when=ALL_COMPLETED)

# Merge all results that finished within 5s
results = [task.result() for task in done if not task.exception()]
# Prioritize by quality: papers > wikipedia > educational
merged = prioritize_sources(results)
```

**Pros:**
- Fast (5s max)
- Gets multiple sources (better quality)
- Graceful degradation (use what we get)
- Can merge results for better answers

**Cons:**
- Slightly slower than pure race (but more reliable)

### Option 3: Streaming (Advanced)
```python
# Show results as they arrive
async for source, data in stream_api_results(query):
    # Send partial result to user immediately
    await websocket.send(f"Found papers from {source}...")
    # LLM summarizes incrementally
    partial_summary = await groq.summarize(data)
    await websocket.send(partial_summary)
```

**Pros:**
- Perceived as instant (user sees progress)
- Best UX for chatbot
- Can show "thinking" animation

**Cons:**
- Requires WebSocket (more complex frontend)
- LLM costs accumulate per partial update

## 🎨 Recommended Design

### Phase 1: Fast Parallel Search (Immediate)
1. **Parallel API calls** with 5s timeout
2. **Use all responses** within timeout window
3. **Prioritize quality**: Research papers > Wikipedia > Educational
4. **Single Groq call** to summarize merged results
5. **Return with citations**

```python
async def fast_conversational_search(query: str):
    # 1. Launch all APIs (no waiting)
    api_tasks = {
        'semantic_scholar': fetch_semantic_scholar(query),
        'wikipedia': fetch_wikipedia(query),
        'arxiv': fetch_arxiv(query),
        'openalex': fetch_openalex(query)
    }
    
    # 2. Wait up to 5s for any results
    done, pending = await asyncio.wait(
        api_tasks.values(), 
        timeout=5.0,
        return_when=ALL_COMPLETED
    )
    
    # 3. Collect all successful responses
    results = []
    for name, task in api_tasks.items():
        if task in done and not task.exception():
            results.append({'source': name, 'data': task.result()})
    
    # 4. Merge & prioritize (papers > wiki)
    merged = merge_results(results)
    
    # 5. Single Groq call to summarize
    summary = await groq_summarize(merged, query)
    
    return {
        'answer': summary,
        'citations': extract_citations(merged),
        'sources': [r['source'] for r in results],
        'response_time': 5.0  # Max
    }
```

**Expected Performance:**
- 2-3s: Wikipedia arrives
- 3-5s: SemanticScholar/OpenAlex arrive
- 5s: Timeout, use what we have
- 6-7s: Groq summarizes (1-2s)
- **Total: 6-7s** (vs current 7-10s)

### Phase 2: Conversation Memory (Easy Add-On)
```python
# Store conversation in-memory dict (free!)
conversations = {}  # {session_id: [messages]}

async def chat_with_memory(query: str, session_id: str):
    # 1. Get conversation history
    history = conversations.get(session_id, [])
    
    # 2. Run search (from Phase 1)
    result = await fast_conversational_search(query)
    
    # 3. Add context to Groq prompt
    prompt = f"""
    Conversation history:
    {format_history(history[-5:])}  # Last 5 exchanges
    
    User: {query}
    Research findings: {result['answer']}
    
    Respond conversationally. If user makes false claim, 
    politely correct with citations.
    """
    
    response = await groq.chat(prompt)
    
    # 4. Save to memory
    history.append({'user': query, 'assistant': response})
    conversations[session_id] = history
    
    return response
```

**Still FREE:** In-memory dict costs nothing

### Phase 3: Statement Verification (Your Key Feature!)
```python
async def verify_statement(statement: str):
    """User says: 'Women are better leaders than men'
    System: Searches evidence, gives balanced view with citations"""
    
    # 1. Extract claim
    claim = extract_claim(statement)  # "women leadership effectiveness"
    
    # 2. Search supporting AND opposing evidence
    pro_papers = await search_papers(f"{claim} supporting evidence")
    con_papers = await search_papers(f"{claim} counterarguments")
    
    # 3. Groq generates balanced response
    prompt = f"""
    User claims: {statement}
    
    Supporting evidence: {pro_papers}
    Counterevidence: {con_papers}
    
    Provide balanced analysis with citations. If claim is 
    one-sided, present nuanced view.
    """
    
    return await groq.chat(prompt)
```

## 💰 Cost Analysis

| Component | Current | After Optimization | Notes |
|-----------|---------|-------------------|-------|
| Groq API | FREE (30 req/min) | FREE | Enough for 1800 queries/hour |
| Data APIs | FREE | FREE | All have generous free tiers |
| Memory | FREE (in-memory) | FREE | Or Redis free tier (Upstash) |
| Hosting | Local | FREE | Railway/Vercel free tier |
| **TOTAL** | **$0/month** | **$0/month** | ✅ |

## 🚀 Implementation Priority

### Week 1: Speed Optimization ⚡
- [ ] Implement parallel API calls with timeout window
- [ ] Test with suicide/mental health queries (your example)
- [ ] Verify 6-7s response time
- [ ] Add citation formatting

### Week 2: Conversational Features 💬
- [ ] Add session-based memory (in-memory dict)
- [ ] Track last 5-10 exchanges per user
- [ ] Test multi-turn conversations
- [ ] Add "Did I answer your question?" prompts

### Week 3: Statement Verification 🔍
- [ ] Detect claims vs questions
- [ ] Search both supporting/opposing evidence
- [ ] Generate balanced responses
- [ ] Add confidence scores

## 📊 Expected Results

**Query: "Why are men more prone to suicide?"**

Current system (7-10s):
```
[7s] Searching SemanticScholar...
[10s] Here's what research says:
Men have 3.7x higher suicide rates due to:
1. Gender norms (seeking help = weakness)
2. Lethal methods (firearms vs overdose)
3. Social isolation in crisis
[Citations: 3 papers]
```

Optimized system (6-7s):
```
[3s] Found 5 papers + Wikipedia article
[6s] Research shows men's suicide rates are 
3.7x higher due to socialization patterns, 
help-seeking stigma, and method choice.

Would you like me to explain any factor in detail?

📚 Sources:
- Möller-Leimkühler (2003): Gender differences
- Canetto & Sakinofsky (1998): Methods study
[+ 3 more]
```

**Follow-up: "But isn't that just because men are weaker?"**
```
[6s] That's actually a common misconception. 
Research indicates the opposite - traditional 
masculine norms pressure men to appear "strong" 
even in crisis, preventing help-seeking behavior.

Studies show:
- Men seek mental health help 50% less (Addis, 2008)
- "Strength" narrative increases risk (Coleman, 2015)

The issue is social conditioning, not weakness.

[Citations included]
```

## 🏆 Key Advantages of Your Approach

1. **Speed**: 6-7s (race condition for data)
2. **Quality**: Multiple sources merged
3. **Conversational**: Memory of past exchanges
4. **Evidence-based**: Always cites research
5. **Free**: $0 operating cost
6. **Scalable**: Free tier = 1800 queries/hour

## ⚠️ Limitations to Consider

1. **Groq free tier**: 30 req/min (sufficient for personal/small use)
   - If you hit limit: $0.10 per 1M tokens (very cheap)
   
2. **API rate limits**: SemanticScholar can return 429 errors
   - Solution: Wikipedia fallback always works
   
3. **Context window**: Groq has 8k token limit
   - Solution: Summarize old messages after 10 exchanges

4. **No persistent storage**: Conversations lost on restart
   - Solution: Add SQLite (still free) if needed

## 🎯 Next Steps

Ready to implement? I recommend:
1. **Start with timeout window approach** (best balance)
2. **Add conversation memory** (5 lines of code)
3. **Test with your example queries**
4. **Upgrade to streaming later** (if needed)

Want me to implement Option 2 (timeout window) right now?
