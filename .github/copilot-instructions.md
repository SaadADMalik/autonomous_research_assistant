# Copilot Instructions - Production-Grade Engineering

## Core Engineering Philosophy

Think like a practical senior software engineer with 5+ years of production experience. Write code that survives real-world conditions, not just ideal scenarios. Every decision should minimize blast radius while maintaining functionality.

---

## 1. Blast Radius & Failure Isolation

**Always ask: "What breaks if this fails?"**

### Critical Rules
- **Default to graceful degradation** - Never let one component failure cascade to the entire system
- **Fail fast at boundaries** - Validate inputs early, return errors/empty results instead of raising exceptions that crash the app
- **Circuit breaker pattern** - If external APIs fail (Semantic Scholar, Wikipedia), immediately switch to fallback without retry storms
- **Isolate side effects** - Database writes, file I/O, external calls should never block critical paths
- **Timeout everything** - Every network call, every subprocess, every lock acquisition must have a timeout

### Examples
```python
# ❌ BAD - One API failure kills entire pipeline
papers = await semantic_scholar.search(query)  # If this fails, everything fails

# ✅ GOOD - Isolated failure with fallback
try:
    papers = await semantic_scholar.search(query)
    if not papers:
        papers = get_educational_fallback(query)
except Exception as e:
    logger.warning(f"API failed: {e}")
    papers = get_educational_fallback(query)
```

---

## 2. Concurrency & Race Conditions

**Assume everything runs concurrently in production.**

### Critical Rules
- **Stateless by default** - Class instances shared across requests = race conditions waiting to happen
- **Immutable data structures** - If data is shared, make it read-only
- **Lock only when necessary** - But when you do, always use timeouts and document the critical section
- **Avoid shared mutable state** - Singletons are acceptable ONLY for read-only resources (models, config)
- **Be explicit about thread safety** - Document in comments if something is NOT thread-safe

### Examples
```python
# ❌ BAD - Shared mutable state
class Orchestrator:
    def __init__(self):
        self.current_query = None  # Race condition if multiple requests
        self.results = []  # Disaster waiting to happen

# ✅ GOOD - No shared state, everything passed as parameters
class Orchestrator:
    def __init__(self):
        self.researcher = ResearcherAgent()  # Stateless agent
    
    async def run_pipeline(self, query: str, documents: List[dict]):
        # All state is local to this call
        results = []
        ...
```

---

## 3. Resource Management

**Memory leaks and connection exhaustion are real.**

### Critical Rules
- **Close what you open** - Use context managers (`async with`, `with`) for resources
- **Limit collection sizes** - Never append to unbounded lists; use max_results everywhere
- **Clear large objects** - Explicitly del large model outputs after processing
- **Connection pooling** - Reuse HTTP sessions, don't create new ones per request
- **Avoid model reloads** - Cache expensive models (transformers) as singletons with lazy init

### Examples
```python
# ❌ BAD - Creates new session per request (socket exhaustion)
async def fetch_papers(query):
    async with aiohttp.ClientSession() as session:
        return await session.get(url)

# ✅ GOOD - Reuse session across requests
class DataFetcher:
    def __init__(self):
        self._session = None
    
    async def _get_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session
```

---

## 4. Error Handling - Real World

**Users don't read tracebacks. Log them, but return useful messages.**

### Critical Rules
- **Three-tier error handling**:
  1. **Operational errors** → Log warning, return fallback, continue (API rate limit, network timeout)
  2. **Input errors** → Return clear user message, no stack trace (empty query, invalid format)
  3. **Fatal errors** → Log full traceback, return generic 500, alert monitoring (DB connection failed)
- **Never expose internal paths** - Sanitize error messages sent to users
- **Rate limit retries** - 3 attempts max with exponential backoff, then give up
- **Log context, not just errors** - Include query, user_id, request_id in every log

### Examples
```python
# ✅ GOOD - Contextual error handling
try:
    papers = await api.search(query)
except asyncio.TimeoutError:
    logger.warning(f"API timeout for query='{query}', using fallback")
    return fallback_data  # Operational error - degrade gracefully
except ValueError as e:
    logger.info(f"Invalid input: {e}")
    raise HTTPException(400, "Query format invalid")  # Input error - tell user
except Exception as e:
    logger.error(f"Fatal error query='{query}': {e}", exc_info=True)
    raise HTTPException(500, "Internal error")  # Fatal - hide details
```

---

## 5. Performance - Production Reality

**Slow is worse than wrong in production.**

### Critical Rules
- **Profile before optimizing** - But know the obvious wins: N+1 queries, synchronous I/O in loops, regex on large text
- **Async for I/O-bound, not CPU-bound** - Don't await CPU work (embeddings, clustering)
- **Batch when possible** - Embed 100 docs at once, not one-by-one
- **Cache aggressively** - But with TTL and size limits (Redis > in-memory dict for multi-instance deployments)
- **Pagination everything** - Never load all N items; limit to 100 max per request

### Examples
```python
# ❌ BAD - Sequential API calls
for doc in documents:
    await fetch_citations(doc.url)  # 10 docs = 10 seconds

# ✅ GOOD - Parallel with concurrency limit
async with asyncio.TaskGroup() as tg:
    tasks = [tg.create_task(fetch_citations(doc.url)) 
             for doc in documents[:10]]  # Limit to 10
```

---

## 6. Observability - Debug Production Issues

**If you can't measure it, you can't fix it.**

### Critical Rules
- **Structured logging** - JSON logs with query_id, user_id, duration, status
- **Log levels matter** - DEBUG (local dev), INFO (request lifecycle), WARNING (degraded), ERROR (needs human)
- **Metrics over logs** - Count success/failure rates, track latencies (p50, p95, p99)
- **Correlation IDs** - Pass request_id through entire call chain
- **Health checks** - Expose `/health` endpoint that actually checks dependencies (DB, external APIs)

### Examples
```python
# ✅ GOOD - Structured, searchable logs
logger.info("pipeline_complete", extra={
    "query_id": request_id,
    "query": query[:50],
    "confidence": confidence,
    "duration_ms": int((time.time() - start) * 1000),
    "document_count": len(documents),
    "source_breakdown": sources
})
```

---

## 7. Testing - Real-World Coverage

**Unit tests catch syntax errors. Integration tests catch production bugs.**

### Critical Rules
- **Test failure paths** - Most bugs are in error handling, not happy path
- **Test with production-like data** - Empty strings, None, 1M+ char inputs, Unicode edge cases
- **Mock external dependencies** - Never call real APIs in tests (flaky, slow, expensive)
- **Isolate test state** - Each test gets fresh DB, fresh cache, fresh models
- **Timeouts in tests** - Any test running >5s is too slow or blocking

### Examples
```python
# ✅ GOOD - Test the failure mode
@pytest.mark.asyncio
async def test_api_timeout_fallback(mocker):
    mocker.patch("api.search", side_effect=asyncio.TimeoutError)
    result = await orchestrator.run_pipeline("quantum physics", [])
    assert result.confidence > 0  # Should use fallback, not crash
```

---

## 8. Security - Practical Paranoia

**Assume all inputs are malicious.**

### Critical Rules
- **Validate, sanitize, escape** - Query strings, file paths, user IDs
- **No secrets in code** - Use environment variables, never commit API keys
- **Rate limit endpoints** - 10 req/min per IP for expensive operations
- **HTTPS only in production** - Redirect HTTP → HTTPS
- **Audit external dependencies** - pip-audit, snyk, or dependabot

---

## 9. Code Style - Pragmatic Clean Code

**Readable code is maintainable code.**

### Critical Rules
- **Docstrings for public methods** - But skip obvious getters/setters
- **Type hints on function signatures** - Helps catch bugs before runtime
- **Keep functions under 50 lines** - If longer, break into helper functions
- **Avoid deep nesting** - Max 3 levels; use early returns
- **Naming: be obvious** - `fetch_papers()` > `get_data()`, `is_rate_limited` > `check()`

---

## 10. Deployment - Zero-Downtime Mindset

**Every deploy could break production. Plan accordingly.**

### Critical Rules
- **Feature flags** - New code paths hidden behind `if config.enable_new_feature`
- **Backward compatibility** - API changes need versioning (/v1/, /v2/)
- **Database migrations** - Additive changes only (add column, then backfill, then remove old)
- **Rollback plan** - Every deploy should be revertible in <5 minutes
- **Smoke tests** - Automated health check after deploy before routing traffic

---

## Summary Checklist (Before Committing)

- [ ] Will this crash if an API times out?
- [ ] Can this cause a memory leak with 1000 concurrent requests?
- [ ] Are errors logged with enough context to debug?
- [ ] Is there a fallback if this fails?
- [ ] Can a malicious user abuse this endpoint?
- [ ] Will this work with empty/null/huge inputs?
- [ ] Is this code readable to someone new 6 months from now?

**The best code is code that survives production.**
