from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from datetime import datetime
from src.data_fetcher import DataFetcher
from src.utils.logger import setup_logging
from src.utils.spell_check import SpellChecker

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

# ✅ ONLY CHANGE: Initialize once at startup instead of per-request
spell_checker = SpellChecker()
data_fetcher = DataFetcher()

# Lazy-load orchestrator
_orchestrator_instance = None

def get_orchestrator():
    """Get or create orchestrator singleton"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        from src.pipelines.orchestrator import Orchestrator
        logger.info("🔧 Initializing Orchestrator (first request)")
        _orchestrator_instance = Orchestrator()
    return _orchestrator_instance

class QueryRequest(BaseModel):
    query: str
    max_results: int = 5

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
    """Generate a research summary for the given query with full source tracking."""
    try:
        original_query = request.query
        logger.info(f"🔍 NEW REQUEST: Received query '{original_query}' from user")
        
        if not original_query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Apply spell correction
        corrected_query = spell_checker.correct_query(original_query)
        spell_corrected = corrected_query != original_query.lower()
        
        if spell_corrected:
            logger.info(f"📝 SPELL CORRECTION: '{original_query}' → '{corrected_query}'")
        
        # Fetch documents from all sources using corrected query
        documents = await data_fetcher.fetch_all(corrected_query, max_results=request.max_results)
        
        logger.info(f"📊 DOCUMENTS FETCHED: {len(documents)} total documents")
        
        if not documents:
            logger.warning(f"📭 NO DOCUMENTS: No documents found for query '{corrected_query}'")
            raise HTTPException(status_code=404, detail="No documents found for the query")
        
        # Analyze source breakdown
        sources_breakdown = {}
        api_status = {}
        content_types = {}
        
        for doc in documents:
            source = doc.get('source', 'unknown')
            content_type = doc.get('content_type', 'unknown')
            
            sources_breakdown[source] = sources_breakdown.get(source, 0) + 1
            content_types[content_type] = content_types.get(content_type, 0) + 1
        
        # Determine API status
        api_status['semantic_scholar'] = 'success' if any(d.get('source') == 'semantic_scholar' for d in documents) else 'rate_limited'
        api_status['wikipedia'] = 'success' if any(d.get('source') == 'wikipedia' for d in documents) else 'not_used'
        api_status['educational_fallback'] = 'active' if any(d.get('source') == 'educational_content' for d in documents) else 'inactive'
        
        logger.info(f"📈 SOURCES: {sources_breakdown}")
        logger.info(f"🔧 API STATUS: {api_status}")
        
        # ✅ ONLY CHANGE: Use singleton instead of creating new instance
        orchestrator = get_orchestrator()
        result = await orchestrator.run_pipeline(original_query, documents)
        
        # Check for pipeline failures
        if not result.result and result.confidence == 0.0:
            error_msg = result.metadata.get("error", "Pipeline processing failed")
            logger.error(f"💥 PIPELINE FAILED: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Pipeline error: {error_msg}")
        
        # Build comprehensive response
        response = {
            "result": result.result,
            "confidence": result.confidence,
            "metadata": {
                "query_info": {
                    "original_query": original_query,
                    "corrected_query": corrected_query if spell_corrected else None,
                    "spell_corrected": spell_corrected,
                    "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "sources_info": {
                    "total_documents": len(documents),
                    "sources_breakdown": sources_breakdown,
                    "content_types": content_types,
                    "source_urls": [doc.get("url") for doc in documents if doc.get("url")]
                },
                "api_status": api_status,
                "data_quality": {
                    "real_research_papers": sources_breakdown.get('semantic_scholar', 0),
                    "educational_content": sources_breakdown.get('educational_content', 0),
                    "wikipedia_articles": sources_breakdown.get('wikipedia', 0),
                    "quality_score": _calculate_quality_score(sources_breakdown)
                },
                "system_info": {
                    "pipeline_source": result.metadata.get("source", "unknown"),
                    "processing_time": "< 1 minute",
                    "api_version": "1.0.0"
                }
            }
        }
        
        logger.info(f"✅ SUCCESS: Generated summary with {result.confidence:.2f} confidence")
        logger.info(f"📊 QUALITY SCORE: {response['metadata']['data_quality']['quality_score']}/10")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 SYSTEM ERROR: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def _calculate_quality_score(sources_breakdown: dict) -> float:
    """Calculate a quality score based on source types (0-10 scale)."""
    score = 0.0
    
    # Real research papers get highest score
    real_papers = sources_breakdown.get('semantic_scholar', 0)
    score += min(real_papers * 3.0, 7.0)  # Max 7 points for real papers
    
    # Wikipedia gets medium score
    wikipedia = sources_breakdown.get('wikipedia', 0)
    score += min(wikipedia * 1.5, 2.0)  # Max 2 points for Wikipedia
    
    # Educational content gets lower score
    educational = sources_breakdown.get('educational_content', 0)
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