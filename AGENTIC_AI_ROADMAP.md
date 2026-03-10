# 🤖 True Agentic AI Transformation Roadmap

**Project:** Autonomous Research Assistant  
**Goal:** Transform from fixed pipeline to truly autonomous reasoning agent  
**Target Performance:** 5-10 seconds per query  
**Date Created:** March 9, 2026

---

## 📊 Current State Assessment

### What We Have (NOT Agentic)
```
Fixed Pipeline:
User Query → Fetch Papers → Summarize → Review → Return Result
```

**Problems:**
- ❌ No reasoning or decision-making
- ❌ No self-evaluation of results
- ❌ No iterative refinement
- ❌ No query understanding/reformulation
- ❌ Takes 10-30 seconds (too slow)
- ❌ Crashes on big queries
- ❌ Poor search results for colloquial queries ("why men suicide more")
- ❌ BART summarizer: 10-20 seconds, memory-hungry, mediocre quality
- ❌ Model cache exists but not wired (cold start every request)

### What Makes AI "Agentic"
✅ **Reasoning** - Evaluates its own output quality  
✅ **Autonomy** - Makes decisions without human intervention  
✅ **Iterative** - Tries different approaches if first attempt fails  
✅ **Goal-Oriented** - Understands objectives and optimizes for them  
✅ **Self-Correcting** - Learns from failures within a session  

---

## 🎯 Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER QUERY                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Query Rewriter Agent       │
         │  (Academic Formulation)     │
         └─────────────┬───────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Reasoning Loop (Max 3x)    │◄─────┐
         │  ┌─────────────────────┐    │      │
         │  │ 1. Search Papers    │    │      │
         │  │ 2. Evaluate Quality │    │      │
         │  │ 3. Decision:        │    │      │
         │  │    - Good? Continue │    │      │
         │  │    - Bad? Reformulate    │      │
         │  └─────────────────────┘    │      │
         └─────────────┬───────────────┘      │
                       │                       │
                 Retry Loop ───────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Parallel Processing:       │
         │  - Extractive Summary       │
         │  - Paper Clustering         │
         │  - Citation Extraction      │
         └─────────────┬───────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Report Generator           │
         │  (Structured Output)        │
         └─────────────┬───────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  RESPONSE      │
              │  (5-10 seconds)│
              └────────────────┘
```

---

## 📋 Phase 1: Speed Optimization (Target: 5-10 sec)

**Goal:** Cut response time from 10-30s to 5-10s without breaking functionality

### 1.1 Kill BART Summarizer ⚡
**Problem:** BART takes 10-20 seconds and uses 2GB RAM  
**Solution:** Replace with extractive summarization

**Implementation:**
```python
# src/agents/summarizer_agent.py - NEW VERSION

class SummarizerAgent:
    def __init__(self):
        # No model loading - pure extractive
        self.sentence_scorer = SentenceScorer()
    
    async def run(self, input_data: AgentInput) -> AgentOutput:
        # Extract top sentences by relevance
        sentences = self._split_sentences(input_data.context)
        scored = self.sentence_scorer.score(input_data.query, sentences)
        top_sentences = sorted(scored, key=lambda x: x.score, reverse=True)[:10]
        summary = " ".join(s.text for s in top_sentences)
        
        return AgentOutput(
            result=summary,
            confidence=0.85,
            metadata={"method": "extractive", "time_ms": 200}
        )
```

**Time Saved:** 10-20 seconds → 0.2 seconds  
**Quality:** Same or better for research papers (BART hallucinates)

---

### 1.2 Wire Model Cache 🔌
**Problem:** Models reload on every request (5-10 sec cold start)  
**Solution:** Use existing `ModelCache` singleton

**Files to Modify:**
- `src/main.py` - Add `ModelCache.initialize()` at startup
- `src/rag/pipeline.py` - Use `ModelCache.get_embedding_model()`
- `src/pipelines/orchestrator.py` - Cache agents as singletons

**Implementation:**
```python
# src/main.py
from src.rag.model_cache import ModelCache

@app.on_event("startup")
async def startup():
    logger.info("🚀 Initializing model cache...")
    ModelCache.initialize()
    logger.info("✅ Startup complete")

# src/rag/pipeline.py
from .model_cache import ModelCache

class RAGPipeline:
    def __init__(self):
        self.embedding_model = ModelCache.get_embedding_model()
        self.vector_store = ModelCache.get_vector_store()
```

**Time Saved:** First request: no change. All subsequent: -5 seconds

---

### 1.3 Parallel Operations 🔀
**Problem:** Sequential processing (fetch → embed → cluster → summarize)  
**Solution:** Run independent operations in parallel

**Implementation:**
```python
# In orchestrator.py
async def run_pipeline(self, query, documents):
    # ... existing code ...
    
    # Parallel post-processing
    cluster_task = asyncio.create_task(self.clusterer.cluster(docs))
    citation_task = asyncio.create_task(self.citation_extractor.extract(docs))
    summary_task = asyncio.create_task(self.summarizer.run(summary_input))
    
    clusters, citations, summary = await asyncio.gather(
        cluster_task, citation_task, summary_task
    )
```

**Time Saved:** ~2-3 seconds

---

### 1.4 Add Timeouts Everywhere ⏱️
**Problem:** Hangs forever if API/model stalls  
**Solution:** Timeout all async operations

**Implementation:**
```python
import asyncio

async def search_with_timeout(query):
    try:
        return await asyncio.wait_for(
            semantic_scholar.search(query),
            timeout=10.0  # 10 seconds max
        )
    except asyncio.TimeoutError:
        logger.warning("Search timeout, using fallback")
        return get_educational_fallback(query)
```

**Apply to:** API calls, model inference, database queries

---

## 📋 Phase 2: True Agentic Behavior (The Core)

**Goal:** Add reasoning, evaluation, and iterative refinement

### 2.1 Query Rewriter Agent 📝

**Purpose:** Transform colloquial queries into academic search terms

**Examples:**
- "why men suicide more" → "male suicide rates gender disparity psychological factors"
- "AI in healthcare" → "artificial intelligence applications healthcare diagnosis treatment"
- "climate change effects" → "climate change impact environmental consequences"

**Implementation:**
```python
# src/agents/query_rewriter_agent.py

class QueryRewriterAgent:
    """
    Reformulates user queries for academic search.
    Uses rule-based + small LLM (API or local distilGPT).
    """
    
    TRANSFORMATIONS = {
        "why": "factors contributing to",
        "how": "mechanisms of",
        "what causes": "etiology of",
        "men": "male",
        "women": "female",
        "suicide": "suicide rates suicidal behavior",
        "more": "higher prevalence increased rates",
        # ... more mappings
    }
    
    SYNONYMS = {
        "AI": ["artificial intelligence", "machine learning", "deep learning"],
        "healthcare": ["medical", "clinical", "health"],
        "climate change": ["global warming", "climate crisis", "environmental change"],
    }
    
    def rewrite(self, query: str, attempt: int = 0) -> str:
        """
        Attempt 0: Basic keyword expansion
        Attempt 1: Add synonyms
        Attempt 2: Broader search terms
        """
        if attempt == 0:
            return self._expand_keywords(query)
        elif attempt == 1:
            return self._add_synonyms(query)
        else:
            return self._broaden_search(query)
    
    def _expand_keywords(self, query: str) -> str:
        # Transform casual language to academic
        result = query.lower()
        for casual, academic in self.TRANSFORMATIONS.items():
            result = result.replace(casual, academic)
        return result
    
    def _add_synonyms(self, query: str) -> str:
        # Add domain synonyms
        for term, synonyms in self.SYNONYMS.items():
            if term.lower() in query.lower():
                query = f"{query} {' '.join(synonyms)}"
        return query
    
    def _broaden_search(self, query: str) -> str:
        # Remove overly specific terms, keep core concepts
        words = query.split()
        # Keep only important terms (simplified)
        important = [w for w in words if len(w) > 4]
        return " ".join(important[:5])  # Max 5 words
```

---

### 2.2 Quality Evaluator Agent 📊

**Purpose:** Judge if retrieved papers actually answer the query

**Implementation:**
```python
# src/agents/quality_evaluator_agent.py

class QualityEvaluatorAgent:
    """
    Evaluates relevance of papers to query.
    Returns score 0.0-1.0 and decision to continue/retry.
    """
    
    def __init__(self):
        self.embeddings = EmbeddingModel()
    
    async def evaluate(self, query: str, papers: List[dict]) -> dict:
        if not papers:
            return {"score": 0.0, "decision": "retry", "reason": "no_papers"}
        
        # Check semantic similarity
        query_emb = self.embeddings.embed_text(query)
        paper_texts = [f"{p['title']} {p['summary']}" for p in papers]
        paper_embs = self.embeddings.embed_text(paper_texts)
        
        similarities = cosine_similarity(query_emb, paper_embs)
        avg_similarity = np.mean(similarities)
        
        # Check keyword overlap
        query_keywords = set(query.lower().split())
        paper_keywords = set(" ".join(paper_texts).lower().split())
        keyword_overlap = len(query_keywords & paper_keywords) / len(query_keywords)
        
        # Check paper quality indicators
        avg_citations = np.mean([p.get('citations', 0) for p in papers])
        recent_papers = sum(1 for p in papers if p.get('year', 0) > 2020) / len(papers)
        
        # Combined score
        relevance_score = (
            avg_similarity * 0.5 +
            keyword_overlap * 0.3 +
            (avg_citations / 100) * 0.1 +  # Normalize citations
            recent_papers * 0.1
        )
        
        decision = "continue" if relevance_score > 0.6 else "retry"
        
        return {
            "score": float(relevance_score),
            "decision": decision,
            "reason": f"semantic={avg_similarity:.2f}, keywords={keyword_overlap:.2f}",
            "avg_citations": int(avg_citations),
            "recent_papers_pct": f"{recent_papers*100:.0f}%",
            "top_matches": [papers[i]['title'] for i in np.argsort(similarities)[-3:][::-1]]
        }
```

---

### 2.3 Reasoning Orchestrator 🧠 (THE KEY)

**Purpose:** Implements the reasoning loop with retry logic

**Implementation:**
```python
# src/pipelines/reasoning_orchestrator.py

class ReasoningOrchestrator:
    """
    Autonomous reasoning loop with iterative refinement.
    This is what makes the system truly "agentic".
    """
    
    MAX_ATTEMPTS = 3
    TIMEOUT_PER_ATTEMPT = 15  # seconds
    
    def __init__(self):
        self.query_rewriter = QueryRewriterAgent()
        self.quality_evaluator = QualityEvaluatorAgent()
        self.data_fetcher = DataFetcher()
        self.base_orchestrator = Orchestrator()  # Existing pipeline
    
    async def autonomous_research(self, user_query: str) -> AgentOutput:
        """
        Main reasoning loop - tries up to 3 times to get good results.
        
        Flow:
        1. Rewrite query for academic search
        2. Fetch papers
        3. Evaluate quality
        4. If bad → reformulate and retry
        5. If good → proceed to synthesis
        """
        logger.info(f"🧠 REASONING: Starting autonomous research for '{user_query}'")
        start_time = time.time()
        
        original_query = user_query
        current_query = user_query
        best_result = None
        best_score = 0.0
        attempt_log = []
        
        for attempt in range(self.MAX_ATTEMPTS):
            attempt_start = time.time()
            logger.info(f"🔄 ATTEMPT {attempt + 1}/{self.MAX_ATTEMPTS}")
            
            # Step 1: Rewrite query (gets smarter with each attempt)
            if attempt > 0:
                current_query = self.query_rewriter.rewrite(original_query, attempt)
                logger.info(f"📝 Reformulated query: '{current_query}'")
            else:
                current_query = self.query_rewriter.rewrite(original_query, 0)
                logger.info(f"📝 Initial query: '{current_query}'")
            
            # Step 2: Search for papers (with timeout)
            try:
                papers = await asyncio.wait_for(
                    self.data_fetcher.fetch_all(current_query, max_results=10),
                    timeout=self.TIMEOUT_PER_ATTEMPT
                )
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Search timeout on attempt {attempt + 1}")
                attempt_log.append({
                    "attempt": attempt + 1,
                    "query": current_query,
                    "result": "timeout",
                    "duration": time.time() - attempt_start
                })
                continue
            except Exception as e:
                logger.error(f"❌ Search error on attempt {attempt + 1}: {e}")
                attempt_log.append({
                    "attempt": attempt + 1,
                    "query": current_query,
                    "result": "error",
                    "error": str(e),
                    "duration": time.time() - attempt_start
                })
                continue
            
            if not papers:
                logger.warning(f"📭 No papers found on attempt {attempt + 1}")
                attempt_log.append({
                    "attempt": attempt + 1,
                    "query": current_query,
                    "result": "no_papers",
                    "duration": time.time() - attempt_start
                })
                continue
            
            # Step 3: Evaluate quality
            evaluation = await self.quality_evaluator.evaluate(original_query, papers)
            logger.info(f"📊 Quality score: {evaluation['score']:.2f} ({evaluation['reason']})")
            logger.info(f"📈 Top matches: {evaluation['top_matches']}")
            
            attempt_log.append({
                "attempt": attempt + 1,
                "query": current_query,
                "result": "evaluated",
                "quality_score": evaluation['score'],
                "decision": evaluation['decision'],
                "paper_count": len(papers),
                "duration": time.time() - attempt_start
            })
            
            # Step 4: Track best result
            if evaluation['score'] > best_score:
                best_score = evaluation['score']
                best_result = (current_query, papers, evaluation)
                logger.info(f"✨ New best result! Score: {best_score:.2f}")
            
            # Step 5: Decide what to do
            if evaluation['decision'] == 'continue':
                logger.info(f"✅ Good results found (score: {evaluation['score']:.2f}), proceeding to synthesis")
                break
            else:
                logger.info(f"⚠️ Quality too low (score: {evaluation['score']:.2f}), will reformulate and retry")
                if attempt < self.MAX_ATTEMPTS - 1:
                    logger.info(f"🔄 Preparing attempt {attempt + 2}...")
        
        # Step 6: Generate final output with best result
        if best_result is None:
            logger.error("❌ All attempts failed - no valid papers found")
            return AgentOutput(
                result="Unable to find relevant research papers after multiple attempts. Please try rephrasing your query or using more specific academic terms.",
                confidence=0.0,
                metadata={
                    "error": "all_attempts_failed",
                    "attempts": self.MAX_ATTEMPTS,
                    "attempt_log": attempt_log,
                    "total_duration": time.time() - start_time
                }
            )
        
        final_query, final_papers, final_eval = best_result
        logger.info(f"🎯 Using best result from query: '{final_query}' (score: {best_score:.2f})")
        
        # Step 7: Run existing pipeline with best papers
        try:
            result = await asyncio.wait_for(
                self.base_orchestrator.run_pipeline(original_query, final_papers),
                timeout=20.0  # 20 seconds for synthesis
            )
        except asyncio.TimeoutError:
            logger.error("⏰ Synthesis timeout")
            return AgentOutput(
                result="Research completed but summary generation timed out.",
                confidence=best_score * 0.5,
                metadata={
                    "error": "synthesis_timeout",
                    "papers_found": len(final_papers),
                    "reasoning": {
                        "attempts": len(attempt_log),
                        "best_score": best_score,
                        "attempt_log": attempt_log
                    }
                }
            )
        
        # Step 8: Enhance with reasoning metadata
        result.metadata.update({
            "reasoning": {
                "autonomous": True,
                "attempts": len(attempt_log),
                "final_query": final_query,
                "original_query": original_query,
                "relevance_score": best_score,
                "evaluation": final_eval,
                "attempt_log": attempt_log,
                "total_duration": time.time() - start_time,
                "decision_making": "iterative_refinement"
            }
        })
        
        # Adjust confidence based on relevance
        result.confidence = min(0.95, result.confidence * (0.8 + best_score * 0.2))
        
        logger.info(f"✅ REASONING COMPLETE: {len(attempt_log)} attempts, final confidence: {result.confidence:.2f}, duration: {time.time() - start_time:.1f}s")
        
        return result
```

**Key Features:**
- ✅ Tries up to 3 times
- ✅ Learns from failures (reformulates query)
- ✅ Tracks best result across attempts
- ✅ Self-evaluates quality
- ✅ Autonomous decision-making
- ✅ Detailed attempt logging
- ✅ Timeouts on every step

---

### 2.4 Query Decomposition (Advanced) 🔍

**Purpose:** Break complex queries into sub-questions

**Implementation:**
```python
# src/agents/query_decomposer_agent.py

class QueryDecomposerAgent:
    """
    Breaks complex queries into answerable sub-questions.
    """
    
    def should_decompose(self, query: str) -> bool:
        """Check if query needs decomposition"""
        indicators = ["and", "impact of", "effect of", "compare", "relationship between"]
        return any(ind in query.lower() for ind in indicators)
    
    def decompose(self, query: str) -> List[str]:
        """
        "impact of AI on healthcare" →
        [
            "AI diagnosis systems accuracy",
            "AI treatment recommendations effectiveness",
            "AI patient outcome improvements"
        ]
        """
        if not self.should_decompose(query):
            return [query]
        
        # Rule-based decomposition
        if "impact" in query.lower() or "effect" in query.lower():
            return self._decompose_impact_query(query)
        elif "compare" in query.lower():
            return self._decompose_comparison_query(query)
        elif " and " in query.lower():
            return self._decompose_conjunction_query(query)
        else:
            return [query]
    
    def _decompose_impact_query(self, query: str) -> List[str]:
        # Extract topic: "impact of X on Y" → X, Y
        # Return: [X effects, Y outcomes, X-Y relationship]
        # Simplified for now
        return [query]  # TODO: Implement
```

---

## 📋 Phase 3: Production Hardening

**Goal:** Make it bulletproof for real users

### 3.1 Error Boundaries 🛡️

**Every agent wrapped in try-catch with fallback:**

```python
# src/utils/safe_execution.py

async def safe_agent_run(agent, input_data, timeout=10.0):
    """
    Safely execute any agent with timeout and error handling.
    Never crashes - always returns AgentOutput.
    """
    try:
        return await asyncio.wait_for(
            agent.run(input_data), 
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"{agent.__class__.__name__} timeout after {timeout}s")
        return AgentOutput(
            result="", 
            confidence=0.0, 
            metadata={
                "error": "timeout",
                "agent": agent.__class__.__name__,
                "timeout_sec": timeout
            }
        )
    except Exception as e:
        logger.error(f"{agent.__class__.__name__} failed: {e}", exc_info=True)
        return AgentOutput(
            result="", 
            confidence=0.0, 
            metadata={
                "error": str(e),
                "agent": agent.__class__.__name__,
                "error_type": type(e).__name__
            }
        )
```

---

### 3.2 Circuit Breaker for APIs ⚡

**Stop hitting APIs if they're consistently failing:**

```python
# src/utils/circuit_breaker.py

class CircuitBreaker:
    """
    Prevents cascading failures by stopping requests
    to failing services.
    """
    
    def __init__(self, failure_threshold=3, timeout=60):
        self.failures = 0
        self.threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    async def call(self, func, *args, **kwargs):
        # Check if circuit is open
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                logger.info("Circuit breaker: Trying half-open state")
                self.state = "half_open"
            else:
                raise Exception(f"Circuit breaker open - service unavailable for {self.timeout}s")
        
        try:
            result = await func(*args, **kwargs)
            # Success - reset circuit
            if self.state == "half_open":
                logger.info("Circuit breaker: Closing circuit (service recovered)")
            self.failures = 0
            self.state = "closed"
            return result
            
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.failures >= self.threshold:
                logger.error(f"Circuit breaker: Opening circuit after {self.failures} failures")
                self.state = "open"
            
            raise

# Usage
semantic_scholar_breaker = CircuitBreaker(failure_threshold=3, timeout=60)

async def fetch_with_breaker(query):
    try:
        return await semantic_scholar_breaker.call(
            semantic_scholar.search, query
        )
    except Exception:
        logger.warning("Circuit breaker triggered, using fallback")
        return get_educational_fallback(query)
```

---

### 3.3 Rate Limiting 🚦

**Protect against abuse:**

```python
# src/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/generate_summary")
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def generate_summary(request: Request, query_request: QueryRequest):
    # ... existing code
```

**Add to requirements.txt:**
```
slowapi>=0.1.9
```

---

### 3.4 Comprehensive Testing 🧪

**Test suite for agentic behavior:**

```python
# tests/test_agentic_reasoning.py

@pytest.mark.asyncio
async def test_reasoning_loop_retries():
    """Test that reasoning loop retries on low quality"""
    orchestrator = ReasoningOrchestrator()
    
    # Mock to return bad papers first, good papers second
    with patch('data_fetcher.fetch_all') as mock_fetch:
        mock_fetch.side_effect = [
            [],  # Attempt 1: no papers
            good_papers   # Attempt 2: good papers
        ]
        
        result = await orchestrator.autonomous_research("test query")
        
        assert result.metadata['reasoning']['attempts'] == 2
        assert result.confidence > 0.5

@pytest.mark.asyncio
async def test_query_rewriting():
    """Test query rewriter transforms colloquial to academic"""
    rewriter = QueryRewriterAgent()
    
    result = rewriter.rewrite("why men suicide more", attempt=0)
    assert "male" in result.lower()
    assert "suicide rates" in result.lower() or "suicidal behavior" in result.lower()

@pytest.mark.asyncio
async def test_quality_evaluator():
    """Test quality evaluator scores relevance correctly"""
    evaluator = QualityEvaluatorAgent()
    
    # High relevance papers
    good_papers = [
        {"title": "Male Suicide Rates", "summary": "Study of male suicide...", "citations": 100}
    ]
    result = await evaluator.evaluate("male suicide rates", good_papers)
    assert result['score'] > 0.6
    assert result['decision'] == 'continue'
    
    # Low relevance papers
    bad_papers = [
        {"title": "Unrelated Topic", "summary": "Something else...", "citations": 0}
    ]
    result = await evaluator.evaluate("male suicide rates", bad_papers)
    assert result['score'] < 0.6
    assert result['decision'] == 'retry'

@pytest.mark.asyncio
async def test_timeout_handling():
    """Test that timeouts don't crash the system"""
    orchestrator = ReasoningOrchestrator()
    
    # Mock slow API
    async def slow_fetch(*args, **kwargs):
        await asyncio.sleep(20)  # Longer than timeout
        return []
    
    with patch('data_fetcher.fetch_all', side_effect=slow_fetch):
        result = await orchestrator.autonomous_research("test query")
        
        # Should not crash, should return error metadata
        assert result is not None
        assert 'error' in result.metadata or result.confidence == 0.0

@pytest.mark.asyncio 
async def test_end_to_end_agentic_flow():
    """Full integration test of agentic pipeline"""
    orchestrator = ReasoningOrchestrator()
    
    # Real query that historically had issues
    result = await orchestrator.autonomous_research("why men suicide more")
    
    # Should complete without crashing
    assert result is not None
    # Should have reasoning metadata
    assert 'reasoning' in result.metadata
    assert result.metadata['reasoning']['autonomous'] is True
    # Should return something useful
    assert len(result.result) > 50 or result.confidence == 0.0
```

---

## 📊 Success Metrics & KPIs

### Performance Targets
- ✅ **Response time:** 5-10 seconds (95th percentile)
- ✅ **First token:** < 2 seconds
- ✅ **Timeout:** 30 seconds max (hard limit)
- ✅ **Cold start:** < 1 second (with model cache)

### Quality Targets
- ✅ **Relevance score:** > 0.7 (measured by QualityEvaluator)
- ✅ **User satisfaction:** > 80% (needs feedback mechanism)
- ✅ **Retry rate:** < 30% (% of queries needing multiple attempts)
- ✅ **Success rate:** > 95% (returns useful results)

### Reliability Targets
- ✅ **Uptime:** 99.5%
- ✅ **Error rate:** < 2%
- ✅ **Graceful degradation:** 100% (no crashes, always return something)
- ✅ **API fallback rate:** < 10%

### Agentic Behavior Metrics (NEW)
- ✅ **Average reasoning attempts:** 1.3-1.8 (most succeed on first try)
- ✅ **Query reformulation success:** > 70% (2nd attempt finds better papers)
- ✅ **Self-correction rate:** 20-30% (catches bad results and retries)
- ✅ **Decision accuracy:** > 85% (correct continue/retry decisions)

---

## 🔧 Implementation Order

### Week 1: Speed Optimization ⚡
**Days 1-2:**
- ✅ Remove BART, implement extractive summarizer
- ✅ Wire ModelCache to main.py, pipeline.py
- ✅ Add timeouts to all async operations

**Days 3-4:**
- ✅ Implement parallel operations in orchestrator
- ✅ Performance testing: measure improvements
- ✅ Target: < 10 seconds

**Day 5:**
- ✅ Bug fixes and optimization
- ✅ Verify all existing tests still pass

---

### Week 2: Agentic Core 🧠
**Days 1-2:**
- ✅ Build QueryRewriterAgent
- ✅ Build QualityEvaluatorAgent
- ✅ Unit tests for both

**Days 3-4:**
- ✅ Build ReasoningOrchestrator
- ✅ Integrate with existing pipeline
- ✅ End-to-end testing

**Day 5:**
- ✅ Test problematic queries: "why men suicide more"
- ✅ Measure retry rates and relevance scores
- ✅ Tune thresholds and parameters

---

### Week 3: Production Hardening 🛡️
**Days 1-2:**
- ✅ Implement error boundaries
- ✅ Circuit breaker for APIs
- ✅ Rate limiting

**Days 3-4:**
- ✅ Comprehensive test suite (90%+ coverage)
- ✅ Load testing (simulate 100 concurrent users)
- ✅ Memory leak testing

**Day 5:**
- ✅ Documentation updates
- ✅ Performance benchmarks
- ✅ Production deployment prep

---

## 🎯 Definition of Done

**This roadmap is complete when:**

1. ✅ User asks "why men suicide more" → Gets relevant papers in 5-10 seconds
2. ✅ System autonomously retries with reformulated query if results are bad
3. ✅ No crashes on any query (graceful degradation)
4. ✅ All operations have timeouts
5. ✅ 90%+ test coverage for agentic components
6. ✅ Response time: 95th percentile < 10 seconds
7. ✅ Quality evaluator correctly scores relevance
8. ✅ Reasoning loop decides correctly (continue/retry)
9. ✅ Model cache wired (no cold starts after first request)
10. ✅ All existing tests still pass

---

## 📝 Notes & Warnings

### Don't Break These ⚠️
- ✅ Existing `/generate_summary` endpoint contract
- ✅ Backward compatibility with old dashboard
- ✅ Current test suite (should all still pass)
- ✅ Data format for frontend

### Technical Debt to Address
- ❌ BART model (2GB) - **REMOVE**
- ❌ Model cache not wired - **FIX**
- ❌ No timeouts - **ADD**
- ❌ No request IDs - **ADD for tracing**
- ❌ Sequential operations - **PARALLELIZE**

### Future Enhancements (Post-Roadmap)
- Multi-language support
- Citation graph analysis
- Collaborative filtering (learn from user feedback)
- Real-time streaming responses
- PDF full-text parsing
- BM25 hybrid search (keyword + semantic)
- Advanced query decomposition with LLM
- User feedback loop for continuous learning

---

## 🚀 Quick Start After Implementation

Once complete, users will see:

**Before:**
```
Query: "why men suicide more"
Time: 25 seconds
Result: Generic fallback content (API failed)
```

**After:**
```
Query: "why men suicide more"
Attempt 1: "why men suicide more" → Low relevance (score: 0.4)
Attempt 2: "male suicide rates gender disparity" → Good! (score: 0.82)
Time: 7 seconds
Result: 8 relevant papers with synthesis
Metadata: Shows reasoning process, attempts, reformulations
```

---

**Last Updated:** March 9, 2026  
**Status:** 🟢 Planning Complete, Ready for Implementation  
**Next Step:** Phase 1 - Speed Optimization  
**Estimated Total Time:** 3 weeks (15 working days)

**Questions? Issues?** See `/memories/session/agentic_roadmap.md` for session notes.
