# Research Chatbot Transformation Plan
## From Summary Tool → Conversational Research Assistant

**Goal:** Build a scalable, conversational research chatbot that answers ONLY from academic papers, with inline citations, streaming responses, and 6-9s latency.

**Scalability Target:** 50 → 5000+ concurrent users

---

## Architecture Overview

### Current State (Problems)
```
User Query → Retry Loop (3 attempts) → Fetch (5-20s) → LLM (non-streaming) → Summary
```
- ❌ 30-60s latency (retry loops)
- ❌ Single-threaded LLM (blocks other users)
- ❌ No conversation memory
- ❌ No streaming
- ❌ No inline citations
- ❌ Cannot scale beyond 5-10 users

### Target Architecture (Scalable)
```
User Message → 
  ├─ Context Check (0.1s) - Reuse papers from history
  ├─ Fetch (if needed, 3-5s, parallel, no retries)
  ├─ Queue LLM Request (fair scheduler)
  ├─ LLM Inference (2-4s, dedicated workers)
  ├─ Stream Response (token-by-token)
  └─ Save to Conversation DB
```
- ✅ 6-9s first message, 2-4s follow-ups
- ✅ Multi-user LLM queue (100+ concurrent)
- ✅ Conversation memory (persistent)
- ✅ Streaming (real-time typing effect)
- ✅ Inline citations [1], [2], [3]
- ✅ Scales to 5000+ users

---

## 🎯 Phase 1: Performance Foundation (Day 1-2)
**Goal:** Fix latency, get to 6-9s baseline

### Tasks
1. **Disable Retry Loop** (30 min)
   - Set `max_attempts = 1` in orchestrator
   - Remove quality threshold checks for chatbot mode
   - Expected: 30s → 8-12s

2. **Add Fast Mode Flag** (1 hour)
   - New endpoint: `/chat` (fast, no retries)
   - Keep `/generate_summary` (old thorough mode)
   - Config: `CHATBOT_MODE=true`

3. **Profile & Optimize Bottlenecks** (2 hours)
   - Measure each component (fetch, RAG, LLM)
   - Identify slow API calls
   - Add timeouts (3s per API max)

4. **Test with Load** (1 hour)
   - Simulate 10 concurrent users
   - Measure queue time
   - Verify no crashes

### Deliverables
- ✅ 6-9s latency for single query
- ✅ `/chat` endpoint live
- ✅ Performance metrics dashboard

### Success Metrics
- Latency: < 10s for 90% of queries
- No retry loops in chatbot mode
- Backend handles 10 concurrent requests

---

## 🎯 Phase 2: Conversation Memory (Day 3-4)
**Goal:** Enable multi-turn conversations with context

### Tasks
1. **Conversation Database** (3 hours)
   - Schema: `conversations`, `messages`, `paper_cache`
   - Use SQLite (local) or PostgreSQL (production)
   - Store: user messages, assistant responses, papers used, citations

2. **Context Window Management** (2 hours)
   - Track last 5-10 messages per conversation
   - Reuse papers from previous messages
   - Only fetch NEW papers if topic shifts

3. **Conversation API** (2 hours)
   ```python
   POST /chat/{conversation_id}/message
   GET /chat/{conversation_id}/history
   DELETE /chat/{conversation_id}  # Clear history
   ```

4. **Paper Deduplication** (1 hour)
   - Cache papers by DOI/URL
   - Don't re-fetch same papers in same conversation
   - Expected: Follow-up queries 50% faster

### Deliverables
- ✅ Persistent conversation storage
- ✅ Context-aware responses
- ✅ Paper caching per conversation

### Success Metrics
- Follow-up queries: < 5s (reusing cached papers)
- Conversations persist across page reloads
- 100+ conversations stored without slowdown

---

## 🎯 Phase 3: Streaming Responses (Day 5-6)
**Goal:** Real-time token-by-token output like ChatGPT

### Tasks
1. **Streaming LLM Integration** (3 hours)
   ```python
   # Replace ollama.generate() with streaming
   for chunk in ollama.chat(
       model='llama3.2:3b',
       messages=conversation_history,
       stream=True
   ):
       yield chunk['message']['content']
   ```

2. **Server-Sent Events (SSE) Endpoint** (2 hours)
   ```python
   @app.get("/chat/{conversation_id}/stream")
   async def stream_response():
       async def event_generator():
           async for token in llm_stream():
               yield f"data: {json.dumps({'token': token})}\n\n"
       return EventSourceResponse(event_generator())
   ```

3. **Frontend Streaming UI** (3 hours)
   - Replace loading spinner with typing animation
   - Append tokens as they arrive
   - Show "Searching papers..." → "Thinking..." states

4. **Error Handling** (1 hour)
   - Handle stream interruptions
   - Retry on disconnect
   - Timeout after 30s

### Deliverables
- ✅ Token-by-token streaming
- ✅ Real-time typing effect in UI
- ✅ Graceful error recovery

### Success Metrics
- First token appears within 5s
- Smooth streaming (no stuttering)
- Works with 50+ concurrent streams

---

## 🎯 Phase 4: Inline Citations (Day 7-8)
**Goal:** Source every claim with [1], [2], [3] references

### Tasks
1. **Citation Prompt Engineering** (2 hours)
   ```python
   prompt = """You are a research assistant. Answer ONLY using these papers.
   Cite sources inline using [1], [2], [3] format.
   
   Papers:
   [1] Title: "Gender pay gap in STEM" (2023) - Abstract: "..."
   [2] Title: "Women in leadership" (2022) - Abstract: "..."
   [3] Title: "Career flexibility" (2021) - Abstract: "..."
   
   User: {query}
   
   Assistant (cite every claim with [1], [2], or [3]):"""
   ```

2. **Citation Parser** (2 hours)
   - Extract `[1]`, `[2]` from LLM output
   - Map to paper metadata (title, authors, year, URL)
   - Generate formatted references

3. **UI Citation Tooltips** (3 hours)
   - Hover over `[1]` shows paper title + authors
   - Click opens paper URL
   - References section at bottom with full citations

4. **Citation Validation** (1 hour)
   - Ensure LLM doesn't hallucinate citations
   - Warn if citing non-existent paper
   - Fallback: disable citations if LLM misbehaves

### Deliverables
- ✅ Inline citations in responses
- ✅ Clickable reference tooltips
- ✅ Full bibliography at bottom

### Success Metrics
- 80%+ of claims have citations
- No hallucinated citations
- References are clickable and accurate

---

## 🎯 Phase 5: Scalability Infrastructure (Day 9-11)
**Goal:** Handle 5000+ concurrent users without slowdown

### Critical Bottlenecks to Fix

#### 1. **LLM Inference Queue** (Day 9 - 4 hours)
**Problem:** Llama 3.2 on CPU handles 1 request at a time
**Solution:** Multi-worker queue

```python
# Use Celery/RQ for distributed LLM workers
from celery import Celery
celery = Celery('llm_worker', broker='redis://localhost:6379')

@celery.task
def run_llm_inference(conversation_id, prompt):
    return ollama.generate(model='llama3.2:3b', prompt=prompt)

# In API:
task = run_llm_inference.delay(conv_id, prompt)
result = task.get(timeout=30)
```

**Workers:** Run 3-5 Ollama instances on separate CPU cores

**Expected:** 5-10 concurrent LLM requests (was 1)

#### 2. **API Rate Limiting (Day 9 - 2 hours)
**Problem:** OpenAlex, Semantic Scholar have rate limits
**Solution:** Request caching + backoff

```python
# Redis cache for API responses (24h TTL)
@cache.memoize(86400)
def fetch_openalex(query):
    return requests.get(f"https://api.openalex.org/works?search={query}")
```

**Expected:** 90% cache hit rate for common queries

#### 3. **Conversation State Storage** (Day 10 - 3 hours)
**Problem:** In-memory conversations lost on restart
**Solution:** PostgreSQL with connection pooling

```python
# Use SQLAlchemy + connection pooling
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'postgresql://user:pass@localhost/research_chat',
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40
)
```

**Expected:** 10,000+ conversations, 0.1s query time

#### 4. **WebSocket/SSE Connection Management** (Day 10 - 2 hours)
**Problem:** 5000 concurrent SSE streams = high memory
**Solution:** Nginx with buffering + Redis pub/sub

```nginx
# Nginx config for SSE
location /chat/ {
    proxy_pass http://backend;
    proxy_buffering off;  # Essential for SSE
    proxy_read_timeout 3600s;
    keepalive_timeout 3600s;
}
```

**Expected:** 5000+ concurrent streams, < 1MB per connection

#### 5. **Horizontal Scaling** (Day 11 - 4 hours)
**Problem:** Single backend server = SPOF
**Solution:** Docker + load balancer

```yaml
# docker-compose.yml
services:
  backend:
    build: .
    replicas: 3  # 3 API servers
    environment:
      - REDIS_URL=redis://redis:6379
      - DB_URL=postgresql://db:5432/research_chat
  
  llm_worker:
    build: .
    command: celery -A llm_worker worker
    replicas: 5  # 5 LLM workers
  
  redis:
    image: redis:alpine
  
  postgres:
    image: postgres:15
  
  nginx:
    image: nginx:alpine
    ports:
      - "8000:80"
```

**Load Testing:**
```bash
# Simulate 1000 users
locust -f load_test.py --users 1000 --spawn-rate 50
```

### Deliverables
- ✅ Multi-worker LLM queue (5-10 concurrent)
- ✅ Redis caching (90% hit rate)
- ✅ PostgreSQL persistent storage
- ✅ Nginx SSE proxy
- ✅ Docker containerization
- ✅ Load balancer ready

### Success Metrics
- 1000 concurrent users: < 10s latency
- 5000 concurrent users: < 15s latency
- Zero downtime during deployments
- 99.9% uptime

---

## 🎯 Phase 6: Production Polish (Day 12-14)

### Tasks
1. **User Authentication** (Day 12 - 3 hours)
   - Simple API key or OAuth
   - Rate limiting per user (10 queries/min)
   - Usage analytics

2. **Conversation UI Redesign** (Day 12-13 - 6 hours)
   - Chat bubbles (user/assistant)
   - Markdown rendering
   - Code syntax highlighting
   - Copy/share buttons

3. **Advanced Features** (Day 13-14 - 8 hours)
   - "Search for more papers" button
   - Export conversation as PDF
   - Summarize entire conversation
   - Save favorite papers

4. **Monitoring & Alerts** (Day 14 - 3 hours)
   - Prometheus metrics
   - Grafana dashboards
   - Error tracking (Sentry)
   - Uptime monitoring

### Deliverables
- ✅ Production-ready UI
- ✅ User management
- ✅ Monitoring dashboards
- ✅ Export features

---

## 📊 Scalability Benchmarks

### Target Performance (Post Phase 5)

| Metric | Single Server | 3 Servers + Load Balancer |
|--------|---------------|---------------------------|
| **Concurrent Users** | 50-100 | 5000+ |
| **Latency (p50)** | 6-8s | 6-8s |
| **Latency (p99)** | 12s | 15s |
| **Requests/sec** | 10 | 500+ |
| **Cost/month** | $0 (local) | $50-100 (VPS) |

### Infrastructure Options

#### Option A: Local/Development (Free)
- 1 server (your laptop)
- SQLite database
- In-process LLM workers
- **Supports:** 10-50 users
- **Cost:** $0

#### Option B: Small Production ($50/mo)
- 1 VPS (4 CPU, 16GB RAM)
- PostgreSQL + Redis
- 3 LLM workers
- Nginx reverse proxy
- **Supports:** 500-1000 users
- **Cost:** $50/mo (Hetzner, DigitalOcean)

#### Option C: High Scale ($200/mo)
- 3 API servers (2 CPU, 8GB each)
- 5 LLM workers (4 CPU, 16GB each)
- PostgreSQL cluster (replicas)
- Redis cluster
- Load balancer + CDN
- **Supports:** 5000-10,000 users
- **Cost:** $200/mo (AWS, GCP)

---

## 🚀 Phased Rollout Strategy

### Week 1 (Phases 1-2)
- Deploy to localhost
- Test with 1-10 users (you + friends)
- Fix critical bugs
- Measure baseline performance

### Week 2 (Phases 3-4)
- Add streaming + citations
- Beta test with 20-50 users
- Collect feedback
- Optimize prompts

### Week 3 (Phase 5)
- Deploy scalability infrastructure
- Load test with 1000 simulated users
- Fix bottlenecks
- Optimize caching

### Week 4 (Phase 6)
- Public launch
- Monitor performance
- Scale horizontally as needed

---

## 🔥 Critical Technical Decisions

### 1. Database: SQLite vs PostgreSQL
**Recommendation: Start SQLite, migrate to PostgreSQL at 100+ users**

| | SQLite | PostgreSQL |
|------|--------|------------|
| Setup | 0 config | Needs server |
| Performance | 10-100 users | 10,000+ users |
| Cost | Free | $15-30/mo |
| Migration | Easy (same schema) | - |

### 2. LLM: Local vs API
**Recommendation: Keep Llama 3.2 local, add GPT-4 as premium option**

| | Llama 3.2 (Local) | GPT-4 (API) |
|------|-------------------|-------------|
| Cost | $0 | $0.01-0.03/query |
| Latency | 2-4s | 1-2s |
| Quality | 80-85% GPT-3.5 | 100% |
| Scalability | 5-10 concurrent | Unlimited |

**Strategy:**
- Free tier: Llama 3.2 (max 10 queries/day)
- Premium tier: GPT-4 (unlimited)

### 3. Streaming: SSE vs WebSocket
**Recommendation: SSE for simplicity**

| | SSE | WebSocket |
|------|-----|-----------|
| Complexity | Low | High |
| Browser Support | 95% | 98% |
| Reconnect | Auto | Manual |
| Firewall | OK | Blocked sometimes |

---

## 🎯 Success Criteria (End of Phase 6)

### Performance
- ✅ First response: < 10s (p90)
- ✅ Follow-up: < 5s (p90)
- ✅ Streaming starts: < 3s
- ✅ 1000 concurrent users without crash

### Quality
- ✅ 90%+ responses have inline citations
- ✅ Conversations persist across sessions
- ✅ No hallucinated facts (grounded in papers)
- ✅ Natural conversational flow

### Scalability
- ✅ Handles 50 users on laptop
- ✅ Handles 5000 users on $200/mo infra
- ✅ Horizontal scaling tested
- ✅ 99.9% uptime

### User Experience
- ✅ Real-time typing effect
- ✅ Clickable citations
- ✅ Mobile-friendly
- ✅ < 3s perceived latency (streaming)

---

## 🛑 Known Limitations & Tradeoffs

### Llama 3.2 3B Limitations
- **Quality:** 80-85% of GPT-3.5 (not GPT-4)
- **Concurrency:** 5-10 requests max on 1 server
- **Speed:** 2-4s (GPU would be 0.5-1s)

**Mitigation:**
- Use GPT-4 API for premium users
- Consider Llama 70B on GPU for higher quality

### API Rate Limits
- OpenAlex: 100k requests/day (free)
- Semantic Scholar: No official limit but throttles
- ArXiv: No limit

**Mitigation:**
- Aggressive caching (24h)
- Queue requests (max 10/s)
- Fallback to educational content if APIs fail

### Token Context Limits
- Llama 3.2: 2048 tokens (~1500 words context)
- Long papers won't fit entirely

**Mitigation:**
- Use abstracts only (200-300 words)
- Sliding window for long conversations
- Summarize old messages after 10 turns

---

## 💰 Cost Breakdown (Monthly)

### Development (Phase 1-4)
- **Infrastructure:** $0 (local)
- **APIs:** $0 (free tiers)
- **Time:** 8 days coding
- **Total:** $0

### Production (Phase 5-6)
#### Small Scale (500 users)
- VPS (4 CPU, 16GB): $40/mo
- PostgreSQL: $15/mo
- Redis: Free (self-hosted)
- APIs: $0 (within limits)
- **Total:** $55/mo

#### Medium Scale (5000 users)
- Load Balancer: $10/mo
- API Servers (3x): $90/mo
- LLM Workers (5x): $200/mo
- PostgreSQL: $30/mo
- Redis: $15/mo
- CDN: $10/mo
- **Total:** $355/mo

#### Enterprise (50k users)
- Use GPT-4 API: $1000-3000/mo
- Managed PostgreSQL: $100/mo
- Redis cluster: $50/mo
- Multiple regions: $500/mo
- **Total:** $2000-4000/mo

---

## 📝 Next Steps

### Immediate (Today)
1. Review this plan - approve/reject phases
2. Set up GitHub project board
3. Create phase 1 branch

### This Week (Phase 1)
1. Disable retry loops → test latency
2. Add `/chat` endpoint
3. Profile & optimize

### Decision Points
- **After Phase 2:** Do we like the conversation UX? Iterate or proceed?
- **After Phase 4:** Are citations accurate? Adjust prompts or proceed?
- **After Phase 5:** Load test results acceptable? Scale or optimize?

---

## 🔒 What This Plan Guarantees

✅ **No technical debt** - scalable from day 1  
✅ **Phased rollout** - can stop at any phase if priorities change  
✅ **Real benchmarks** - load test at each phase  
✅ **Cost-effective** - start free, scale as needed  
✅ **Production-ready** - monitoring, error handling, auth built-in  

**Timeline:** 14 days (2 weeks)  
**Cost:** $0 for phases 1-4, $50-200/mo for production  
**Result:** Research chatbot that rivals Perplexity, 100% grounded in papers, scales to 5k users  

---

## 🎯 Your Call

Which phases do you want to start with?
- **Option 1:** Phase 1 only (fix latency, see if you like 6-9s)
- **Option 2:** Phases 1-2 (fast + conversations)
- **Option 3:** Phases 1-4 (full chatbot experience, no scale)
- **Option 4:** All phases (production-ready, scalable)

I recommend **Option 3** for now (Phases 1-4), then evaluate if you need Phase 5 (scalability) based on actual user growth.
