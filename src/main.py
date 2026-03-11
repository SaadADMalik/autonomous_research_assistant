from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
from datetime import datetime
import time
import uuid
import traceback
from typing import Optional
from dotenv import load_dotenv
load_dotenv()  # Auto-load .env file (GROQ_API_KEY, etc.) before any imports that need it
from src.data_fetcher import DataFetcher
from src.utils.logger import setup_logging
from src.utils.spell_check import SpellChecker
from src.rag.model_cache import ModelCache
from src.utils.conversation_manager import ConversationManager

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Autonomous AI Research Assistant", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🛡️ PRODUCTION: Global exception handler - never show raw errors to users
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch all unhandled exceptions and return user-friendly error messages.
    Log the full stack trace for debugging but hide it from users.
    """
    # Log the full error with traceback for debugging
    logger.error(f"💥 UNHANDLED ERROR: {type(exc).__name__}: {str(exc)}")
    logger.error(f"📍 Request: {request.method} {request.url}")
    logger.error(f"🔍 Traceback:\n{traceback.format_exc()}")
    
    # Determine user-friendly message based on error type
    if isinstance(exc, SyntaxError):
        user_message = "The system encountered a configuration error. Our team has been notified."
        status_code = 500
    elif isinstance(exc, ImportError) or isinstance(exc, ModuleNotFoundError):
        user_message = "A required component is missing. Please contact support."
        status_code = 500
    elif isinstance(exc, TimeoutError) or "timeout" in str(exc).lower():
        user_message = "The request took too long. Please try again with a simpler query."
        status_code = 504
    elif isinstance(exc, ValueError):
        user_message = "Invalid input provided. Please check your query and try again."
        status_code = 400
    else:
        user_message = "An unexpected error occurred. Please try again or contact support if the issue persists."
        status_code = 500
    
    # Return clean JSON response (no stack traces)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": type(exc).__name__,
            "message": user_message,
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4())  # For support tickets
        }
    )

# ⚡ Phase 1: Initialize model cache at startup
@app.on_event("startup")
async def startup_event():
    """Initialize expensive resources at startup to speed up first request."""
    logger.info("🚀 APPLICATION STARTUP: Initializing model cache...")
    try:
        ModelCache.initialize()
        logger.info("✅ STARTUP COMPLETE: All models cached and ready")
    except Exception as e:
        logger.error(f"❌ STARTUP ERROR: Failed to initialize cache: {e}", exc_info=True)
        # Don't crash the app - models will lazy-load on first request

# ✅ ONLY CHANGE: Initialize once at startup instead of per-request
spell_checker = SpellChecker()
data_fetcher = DataFetcher()

# 🎯 Phase 2: Conversation manager for memory & follow-ups
conversation_manager = ConversationManager(session_timeout_minutes=30)

# Lazy-load orchestrator
_orchestrator_instance = None

def get_orchestrator():
    """Get or create orchestrator singleton"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        from src.pipelines.orchestrator import Orchestrator
        logger.info("🔧 Initializing Orchestrator (first request)")
        # 🎯 Phase 2: Pass data_fetcher to orchestrator for agentic reasoning loop
        _orchestrator_instance = Orchestrator(data_fetcher=data_fetcher)
    return _orchestrator_instance

class QueryRequest(BaseModel):
    query: str
    max_results: int = 5
    session_id: Optional[str] = None  # 🎯 Phase 2: Session ID for conversation memory

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Autonomous Research Assistant API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "api_version": "1.0.0",
        "services": {
            "semantic_scholar": "available",
            "wikipedia": "available",
            "spell_checker": "available"
        }
    }

@app.post("/generate_summary")
async def generate_summary(request: QueryRequest):
    """Generate a research summary for the given query with full source tracking (thorough mode with retries)."""
    return await _process_query(request, mode="thorough", max_attempts=3)

@app.post("/chat")
async def chat(request: QueryRequest):
    """🎯 PHASE 1: Fast chatbot endpoint - no retries, optimized for speed (6-9s target)."""
    return await _process_query(request, mode="fast", max_attempts=1)

async def _process_query(request: QueryRequest, mode: str = "thorough", max_attempts: int = 3):
    """Internal query processing with performance profiling."""
    start_time = time.time()
    timing_metrics = {}
    
    try:
        original_query = request.query
        
        # 🎯 Phase 2 ENHANCED: LLM-based intent analysis with smart cache filtering
        session_id = request.session_id or str(uuid.uuid4())
        
        # Use LLM to analyze intent and filter cached papers by relevance
        is_follow_up, cached_papers, query_intent = conversation_manager.analyze_query_and_filter_cache(
            session_id=session_id,
            query=original_query
        )
        
        logger.info(f"🔍 NEW REQUEST [{mode.upper()}]: Received query '{original_query}' from user")
        if is_follow_up:
            if cached_papers:
                logger.info(f"🔄 FOLLOW-UP DETECTED: Session {session_id[:8]}..., using {len(cached_papers)} relevant cached papers")
            else:
                logger.info(f"🔄 FOLLOW-UP DETECTED: Session {session_id[:8]}..., but cached papers not relevant, will fetch new")
        
        # Use enhanced search query if available from intent analysis
        query_to_use = original_query
        if query_intent and query_intent.get('search_query'):
            query_to_use = query_intent['search_query']
            if query_to_use != original_query:
                logger.info(f"🎯 Enhanced search query: '{original_query}' → '{query_to_use}'")
        
        if not original_query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Apply spell correction to the query we'll actually use
        spell_start = time.time()
        corrected_query = spell_checker.correct_query(query_to_use)
        spell_corrected = corrected_query != query_to_use.lower()
        timing_metrics['spell_check'] = time.time() - spell_start
        
        if spell_corrected:
            logger.info(f"📝 SPELL CORRECTION: '{query_to_use}' → '{corrected_query}'")
        
        # 🎯 Phase 2: Use agentic pipeline with reasoning loop
        # The orchestrator will handle fetching, quality evaluation, and retry logic
        orchestrator = get_orchestrator()
        
        # 🎯 Phase 2: Get conversation context for LLM
        conversation_context = ""
        if is_follow_up:
            conversation_context = conversation_manager.format_context_for_llm(session_id, max_turns=3)
        
        pipeline_start = time.time()
        result = await orchestrator.run_agentic_pipeline(
            query=corrected_query,
            max_results=request.max_results,
            max_attempts=max_attempts,  # 🎯 Phase 1: Variable attempts (1 for fast mode, 3 for thorough)
            mode=mode,  # 🎯 Phase 1: "fast" skips slow APIs (arXiv=30s, OpenAlex=10s), "thorough" uses all
            conversation_context=conversation_context,  # 🎯 Phase 2: Pass conversation history to LLM
            cached_papers=cached_papers if cached_papers else None  # 🎯 Phase 2: Only use if relevant
        )
        timing_metrics['pipeline_total'] = time.time() - pipeline_start
        
        # Check for pipeline failures
        if not result.result and result.confidence == 0.0:
            error_msg = result.metadata.get("error", "Pipeline processing failed")
            logger.error(f"💥 PIPELINE FAILED: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Pipeline error: {error_msg}")
        
        # 🎯 HYBRID APPROACH: Post-generation validation (0.5s overhead)
        # Validates answer relevance and retries with fresh papers if hallucinating
        validation_result = None
        if query_intent and conversation_manager.intent_analyzer and is_follow_up and cached_papers:
            # Only validate when using cached papers for follow-ups
            validation_start = time.time()
            validation_result = conversation_manager.intent_analyzer.validate_answer_relevance(
                query=original_query,
                answer=result.result,
                query_intent=query_intent
            )
            timing_metrics['validation'] = time.time() - validation_start
            
            # If validation failed (hallucination detected), retry with fresh papers
            if not validation_result.get('is_relevant', True):
                logger.warning(f"⚠️ HALLUCINATION DETECTED: {validation_result.get('reason', 'Unknown')} - Retrying with fresh papers...")
                
                # Retry: Fetch fresh papers and regenerate
                retry_start = time.time()
                result = await orchestrator.run_agentic_pipeline(
                    query=corrected_query,
                    max_results=request.max_results,
                    max_attempts=max_attempts,
                    mode=mode,
                    conversation_context=conversation_context,
                    cached_papers=None  # 🚨 Force fetch fresh papers, don't use cache
                )
                timing_metrics['retry_after_validation'] = time.time() - retry_start
                logger.info(f"✅ RETRY COMPLETE: Generated new answer with fresh papers")
        
        # Extract metadata from agentic pipeline
        reasoning_attempts = result.metadata.get("reasoning_attempts", [])
        final_query = result.metadata.get("final_query", corrected_query)
        
        # 🎯 Phase 4: Get accurate source breakdown from last attempt
        sources_breakdown = {}
        api_status = {}
        document_count = result.metadata.get("document_count", 0)
        
        # Get source breakdown from last successful attempt
        if reasoning_attempts:
            last_attempt = reasoning_attempts[-1]
            sources_breakdown = last_attempt.get("source_breakdown", {})
            apis_used = last_attempt.get("apis_used", [])
            
            # Set realistic API status based on which APIs were used
            api_status['arxiv'] = 'success' if 'arxiv' in apis_used else 'not_used'
            api_status['openalex'] = 'success' if 'openalex' in apis_used else 'not_used'
            api_status['semantic_scholar'] = 'success' if 'semantic_scholar' in apis_used else 'not_used'
            api_status['wikipedia'] = 'success' if sources_breakdown.get('wikipedia', 0) > 0 else 'not_used'
            api_status['educational_fallback'] = 'active' if sources_breakdown.get('educational', 0) > 0 else 'inactive'
        else:
            # Fallback: try to parse from metadata sources (legacy behavior)
            if "sources" in result.metadata:
                for source_url in result.metadata.get("sources", []):
                    if "semanticscholar" in source_url or "arxiv" in source_url:
                        sources_breakdown["semantic_scholar"] = sources_breakdown.get("semantic_scholar", 0) + 1
                    elif "wikipedia" in source_url:
                        sources_breakdown["wikipedia"] = sources_breakdown.get("wikipedia", 0) + 1
                    else:
                        sources_breakdown["educational_content"] = sources_breakdown.get("educational_content", 0) + 1
            
            api_status['semantic_scholar'] = 'success' if sources_breakdown.get('semantic_scholar', 0) > 0 else 'rate_limited'
            api_status['wikipedia'] = 'success' if sources_breakdown.get('wikipedia', 0) > 0 else 'not_used'
            api_status['educational_fallback'] = 'active' if sources_breakdown.get('educational_content', 0) > 0 else 'inactive'
        
        logger.info(f"📈 SOURCES: {sources_breakdown}")
        logger.info(f"🔧 API STATUS: {api_status}")
        
        # Build comprehensive response
        response = {
            "result": result.result,
            "confidence": result.confidence,
            "session_id": session_id,  # 🎯 Phase 2: Return session ID for follow-ups
            "is_follow_up": is_follow_up,  # 🎯 Phase 2: Indicate if this was a follow-up
            "metadata": {
                "query_info": {
                    "original_query": original_query,
                    "corrected_query": corrected_query if spell_corrected else None,
                    "final_query": final_query if final_query != corrected_query else None,
                    "spell_corrected": spell_corrected,
                    "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "intent_analysis": query_intent if query_intent else None  # 🎯 LLM intent analysis results
                },
                "conversation": {  # 🎯 Phase 2: Conversation metadata
                    "session_id": session_id,
                    "is_follow_up": is_follow_up,
                    "cached_papers_used": len(cached_papers) if cached_papers else 0,
                    "cache_relevance": "high" if cached_papers else ("low" if is_follow_up else "n/a"),
                    "conversation_stats": conversation_manager.get_stats()
                },
                "sources_info": {
                    "total_documents": document_count,
                    "sources_breakdown": sources_breakdown,
                    "source_urls": result.metadata.get("sources", [])
                },
                "api_status": api_status,
                "data_quality": {
                    "arxiv_papers": sources_breakdown.get('arxiv', 0),
                    "openalex_papers": sources_breakdown.get('openalex', 0),
                    "semantic_scholar_papers": sources_breakdown.get('semantic_scholar', 0),
                    "real_research_papers": (
                        sources_breakdown.get('arxiv', 0) + 
                        sources_breakdown.get('openalex', 0) + 
                        sources_breakdown.get('semantic_scholar', 0)
                    ),
                    "educational_content": sources_breakdown.get('educational_content', 0) + sources_breakdown.get('educational', 0),
                    "wikipedia_articles": sources_breakdown.get('wikipedia', 0),
                    "quality_score": _calculate_quality_score(sources_breakdown)
                },
                "agentic_reasoning": {
                    "enabled": True,
                    "attempts": reasoning_attempts,
                    "total_attempts": len(reasoning_attempts),
                    "succeeded": not result.metadata.get("all_attempts_failed", False),
                    "final_decision": reasoning_attempts[-1] if reasoning_attempts else None
                },
                "system_info": {
                    "pipeline_source": result.metadata.get("source", "unknown"),
                    "processing_time": f"{time.time() - start_time:.2f}s",
                    "api_version": "1.0.0",
                    "mode": f"agentic_v2_{mode}"
                },
                "performance": {
                    "total_time": round(time.time() - start_time, 2),
                    "breakdown": {
                        "spell_check": round(timing_metrics.get('spell_check', 0), 3),
                        "pipeline": round(timing_metrics.get('pipeline_total', 0), 2)
                    },
                    "mode": mode,
                    "max_attempts": max_attempts,
                    "target_latency": "6-9s" if mode == "fast" else "< 60s"
                },
                "autonomous_agent": {
                    "plan": result.metadata.get("plan", {}),
                    "tool_selection": result.metadata.get("tool_selection", {}),
                    "clusters": result.metadata.get("clusters", []),
                    "citations": result.metadata.get("citations", []),
                    "report_markdown": result.metadata.get("report_markdown", ""),
                    "memory_hits": result.metadata.get("memory_hits", 0),
                    "documents": result.metadata.get("documents", []),  # 🎯 Phase 2: Include documents for caching
                }
            }
        }
        
        logger.info(f"✅ SUCCESS: Generated summary with {result.confidence:.2f} confidence")
        logger.info(f"📊 QUALITY SCORE: {response['metadata']['data_quality']['quality_score']}/10")
        logger.info(f"🤖 AGENTIC: {response['metadata']['agentic_reasoning']['total_attempts']} attempts, succeeded={response['metadata']['agentic_reasoning']['succeeded']}")
        
        # 🎯 Phase 2: Store conversation turn for session memory
        papers_used = response['metadata']['autonomous_agent'].get('documents', [])
        logger.info(f"📄 DEBUG: papers_used count = {len(papers_used)}")
        if papers_used:
            logger.info(f"📄 DEBUG: First paper keys = {list(papers_used[0].keys())}")
        conversation_manager.add_turn(
            session_id=session_id,
            query=original_query,
            response=result.result,
            papers=papers_used,
            confidence=result.confidence
        )
        logger.info(f"💾 Stored conversation turn for session {session_id[:8]}... with {len(papers_used)} papers")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 SYSTEM ERROR: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def _calculate_quality_score(sources_breakdown: dict) -> float:
    """
    Calculate a quality score based on source types (0-10 scale).
    
    🎯 Phase 3: Updated to score arXiv and OpenAlex papers
    """
    score = 0.0
    
    # High-quality academic papers (arXiv, OpenAlex, Semantic Scholar)
    arxiv_papers = sources_breakdown.get('arxiv', 0)
    openalex_papers = sources_breakdown.get('openalex', 0)
    semantic_scholar_papers = sources_breakdown.get('semantic_scholar', 0)
    
    total_academic_papers = arxiv_papers + openalex_papers + semantic_scholar_papers
    score += min(total_academic_papers * 3.0, 7.0)  # Max 7 points for academic papers
    
    # Wikipedia gets medium score
    wikipedia = sources_breakdown.get('wikipedia', 0)
    score += min(wikipedia * 1.5, 2.0)  # Max 2 points for Wikipedia
    
    # Educational content gets lower score
    educational = sources_breakdown.get('educational_content', 0) + sources_breakdown.get('educational', 0)
    score += min(educational * 0.5, 1.0)  # Max 1 point for educational
    
    return round(min(score, 10.0), 1)

@app.get("/status")
async def status():
    """Get detailed system status."""
    return {
        "system_status": "operational",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "services": {
            "semantic_scholar_api": "available",
            "wikipedia_api": "available", 
            "spell_checker": "active",
            "educational_fallback": "ready"
        },
        "capabilities": {
            "real_research_papers": True,
            "educational_content": True,
            "spell_correction": True,
            "source_transparency": True,
            "quality_scoring": True
        },
        "api_info": {
            "version": "1.0.0",
            "endpoints": ["/health", "/generate_summary", "/status"],
            "rate_limits": "semantic_scholar_dependent"
        }
    }

@app.get("/sources")
async def sources_info():
    """Get information about data sources."""
    return {
        "data_sources": {
            "semantic_scholar": {
                "description": "Real research papers from Semantic Scholar API",
                "coverage": "200M+ academic papers",
                "quality": "high",
                "cost": "free",
                "rate_limits": "1 req/sec with API key, burst limits without"
            },
            "wikipedia": {
                "description": "Encyclopedia articles from Wikipedia",
                "coverage": "6M+ articles in English",
                "quality": "medium",
                "cost": "free",
                "rate_limits": "reasonable use"
            },
            "educational_content": {
                "description": "Curated educational content when APIs are unavailable",
                "coverage": "topic-specific academic content",
                "quality": "educational",
                "cost": "free",
                "rate_limits": "none"
            }
        },
        "transparency": {
            "source_labeling": "all content clearly labeled by source",
            "quality_scoring": "0-10 scale based on source mix",
            "api_status": "real-time status of all data sources",
            "fallback_reasoning": "clear indication when and why fallbacks are used"
        }
    }