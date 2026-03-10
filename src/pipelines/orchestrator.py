import logging
import asyncio
import time
from typing import List, Union, Optional, Dict
from src.agents.researcher_agent import ResearcherAgent
from src.agents.summarizer_agent import SummarizerAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.planner_agent import PlannerAgent
from src.agents.query_rewriter_agent import QueryRewriterAgent
from src.agents.quality_evaluator_agent import QualityEvaluatorAgent
from src.utils.logger import setup_logging
from src.agents.base import AgentInput, AgentOutput
from src.pipelines.tool_router import ToolRouter
from src.pipelines.knowledge_enrichment import PaperClusterer, CitationExtractor, ReportGenerator
from src.rag.memory_store import AgentMemoryStore
from difflib import SequenceMatcher

setup_logging()
logger = logging.getLogger(__name__)

# 🎯 PERFORMANCE PROFILING: Track timing for each pipeline stage
class PerformanceProfiler:
    """Track detailed timing for performance analysis."""
    def __init__(self):
        self.timings = {}
        self.start_time = time.time()
        
    def start_stage(self, stage_name: str):
        """Mark start of a stage."""
        self.timings[stage_name] = {'start': time.time()}
        logger.debug(f"⏱️  [{stage_name}] Starting...")
        
    def end_stage(self, stage_name: str, extra_info: str = ""):
        """Mark end of a stage and log duration."""
        if stage_name in self.timings:
            elapsed = time.time() - self.timings[stage_name]['start']
            self.timings[stage_name]['duration'] = elapsed
            self.timings[stage_name]['elapsed_since_start'] = time.time() - self.start_time
            info = f" ({extra_info})" if extra_info else ""
            logger.info(f"⏱️  [{stage_name}] Completed in {elapsed:.2f}s{info}")
        
    def get_summary(self) -> Dict:
        """Get timing summary."""
        total = time.time() - self.start_time
        breakdown = {name: data.get('duration', 0) for name, data in self.timings.items()}
        return {
            'total_time': round(total, 2),
            'breakdown': breakdown,
            'detailed': self.timings
        }

class Orchestrator:
    def __init__(self, data_fetcher=None):
        logger.info("🚀 Initializing Orchestrator")
        try:
            self.planner = PlannerAgent()
            self.router = ToolRouter()
            self.researcher = ResearcherAgent()
            self.summarizer = SummarizerAgent()
            self.reviewer = ReviewerAgent()
            self.clusterer = PaperClusterer()
            self.citation_extractor = CitationExtractor()
            self.report_generator = ReportGenerator()
            self.memory_store = AgentMemoryStore()
            
            # 🎯 Phase 2: Agentic AI agents
            self.query_rewriter = QueryRewriterAgent()
            self.quality_evaluator = QualityEvaluatorAgent()
            
            # Store data fetcher for reasoning loop
            self.data_fetcher = data_fetcher
            
            logger.info("✅ All agents initialized successfully (including Phase 2 agentic agents)")
        except Exception as e:
            logger.error(f"❌ Failed to initialize agents: {str(e)}")
            raise

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts using sequence matching.
        Range: 0.0 to 1.0
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        # Use SequenceMatcher for basic similarity
        similarity = SequenceMatcher(None, text1, text2).ratio()
        return similarity

    def _validate_summary_coherence(self, query: str, summary: str, documents: List[dict]) -> tuple:
        """
        Validate that the summary is coherent with query and documents.
        Returns: (is_valid, confidence_adjustment)
        """
        if not summary or not query:
            return False, 0.0
        
        # Check if summary contains keywords from query
        query_keywords = set(query.lower().split())
        summary_keywords = set(summary.lower().split())
        
        # Remove common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be', 'been', 'of', 'to', 'in', 'for', 'on', 'with', 'by'}
        query_keywords -= common_words
        summary_keywords -= common_words
        
        # Check keyword overlap
        keyword_overlap = len(query_keywords & summary_keywords) / max(len(query_keywords), 1)
        
        logger.debug(f"📊 Keyword overlap: {keyword_overlap:.2f} (query: {query_keywords}, summary: {summary_keywords})")
        
        # Check if summary contains document context
        doc_content = " ".join([d.get("title", "") + " " + d.get("summary", "") for d in documents if isinstance(d, dict)])
        doc_similarity = self._calculate_semantic_similarity(summary, doc_content)
        
        logger.debug(f"📊 Document similarity: {doc_similarity:.2f}")
        
        # Validation criteria
        is_valid = keyword_overlap >= 0.2 or doc_similarity >= 0.15
        confidence_adjustment = keyword_overlap * 0.3 + doc_similarity * 0.2
        
        logger.info(f"🔍 Summary coherence check: valid={is_valid}, adjustment={confidence_adjustment:.2f}")
        
        return is_valid, confidence_adjustment

    async def run_pipeline(self, query: str, documents: List[Union[dict, str]], mode: str = "thorough", conversation_context: str = "") -> AgentOutput:
        logger.info(f"🔄 Running pipeline ({mode.upper()} mode) with query: '{query}'")
        
        # 🎯 Initialize performance profiler
        profiler = PerformanceProfiler()
        
        try:
            # Validate inputs
            if not query or not query.strip():
                logger.error("❌ Empty query provided")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={
                        "source": "orchestrator",
                        "error": "Empty query",
                        "stage": "validation"
                    }
                )
            
            if not documents:
                logger.error("❌ No documents provided")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={
                        "source": "orchestrator",
                        "error": "No documents provided",
                        "stage": "validation"
                    }
                )
            
            # Normalize documents to consistent format
            normalized_docs = []
            for i, doc in enumerate(documents):
                try:
                    if isinstance(doc, str):
                        normalized_doc = {
                            "title": "Text Document",
                            "summary": doc,
                            "url": "",
                            "year": 2025,
                            "source": "text"
                        }
                    elif isinstance(doc, dict):
                        normalized_doc = {
                            "title": doc.get("title", "Untitled"),
                            "summary": doc.get("summary", doc.get("content", "")),
                            "url": doc.get("url", ""),
                            "year": doc.get("year", 2025),
                            "source": doc.get("source", "unknown")
                        }
                    else:
                        logger.warning(f"⚠️ Unexpected document type: {type(doc)}")
                        continue
                    
                    # Validate the document has content
                    if normalized_doc["summary"] and len(normalized_doc["summary"]) > 10:
                        normalized_docs.append(normalized_doc)
                        logger.debug(f"✅ Document {i+1} normalized: {normalized_doc['title'][:50]}...")
                    else:
                        logger.warning(f"⚠️ Document {i+1} has insufficient content")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error normalizing document {i+1}: {str(e)}")
                    continue
            
            if not normalized_docs:
                logger.error("❌ No valid documents after normalization")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={
                        "source": "orchestrator",
                        "error": "No valid documents",
                        "stage": "normalization"
                    }
                )
            
            logger.info(f"✅ Normalized {len(normalized_docs)} documents")

            # ============ PRE-STAGE: Planning, routing, memory management ============
            profiler.start_stage('planning_routing')
            plan = self.planner.create_plan(query)
            tool_selection = self.router.route(query, normalized_docs)
            profiler.end_stage('planning_routing')
            
            # 🎯 Fast mode optimization: Skip expensive VectorStore creation (saves ~5-10s)
            if mode == "thorough":
                profiler.start_stage('vectorstore_creation')
               # 🔥 CRITICAL FIX: ALWAYS use fresh in-memory memory store to prevent ANY pollution
                logger.info("🧹 Creating fresh in-memory memory store (prevents all cross-query pollution)...")
                try:
                    from src.rag.vectorstore import VectorStore
                    # Create completely fresh in-memory store (no disk persistence)
                    self.memory_store.store = VectorStore(
                        use_memory=True,
                        collection_name="agent_memory_temp",
                        embedding_model_name="all-MiniLM-L6-v2",
                        reset_collection=True
                    )
                    logger.info("✅ Fresh memory store created (in-memory only)")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to create fresh memory store: {e}")
                profiler.end_stage('vectorstore_creation')
            else:
                logger.info("⚡ FAST MODE: Skipping VectorStore creation (saves 5-10s)")
                profiler.timings['vectorstore_creation'] = {'duration': 0, 'skipped': True}
            
            logger.info(
                "🧭 Planning complete: %d steps, tools=%s",
                len(plan.get("active_steps", [])),
                tool_selection.get("selected_tools", []),
            )
            
            # ============ STAGE 1: Research ============
            profiler.start_stage('research')
            logger.info("📖 STAGE 1: Research phase starting...")
            research_input = AgentInput(
                query=query, 
                metadata={"source": "orchestrator", "stage": "research"}
            )
            
            # ⚡ Phase 1: Add timeout to research
            try:
                research_output = await asyncio.wait_for(
                    self.researcher.run(research_input, normalized_docs),
                    timeout=15.0  # 15 second timeout for research
                )
            except asyncio.TimeoutError:
                logger.error("❌ Research phase timeout")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={
                        "source": "orchestrator",
                        "error": "Research timeout after 15 seconds",
                        "stage": "research"
                    }
                )
            
            if research_output.confidence == 0.0 or not research_output.result:
                logger.error("❌ Research phase failed")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={
                        "source": "orchestrator",
                        "error": f"Research failed: {research_output.metadata.get('error', 'Unknown')}",
                        "stage": "research"
                    }
                )
            
            profiler.end_stage('research', f"confidence {research_output.confidence:.2f}")
            logger.info(f"✅ STAGE 1 Complete: Research confidence {research_output.confidence:.2f}")
            
            # ============ STAGE 2: Summarization ============
            profiler.start_stage('summarization')
            logger.info("📝 STAGE 2: Summarization phase starting...")
            
            # 🎯 Phase 2: Add conversation context for follow-ups
            query_with_context = query
            if conversation_context:
                query_with_context = conversation_context + "\n" + query
                logger.info("💬 Added conversation context to summarization prompt")
            
            summary_input = AgentInput(
                query=query_with_context,
                context=research_output.result,  # 🔥 FIX: Don't prepend memory_context (causes nested prefixes)
                metadata={"source": "orchestrator", "stage": "summarization", "mode": mode}  # 🎯 Pass mode to summarizer
            )
            
            # ⚡ Phase 1: Dynamic timeout based on mode (1b model ~10s, 3b model ~30s)
            timeout = 15.0 if mode == 'fast' else 40.0
            try:
                summary_output = await asyncio.wait_for(
                    self.summarizer.run(summary_input),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error("❌ Summarization phase timeout")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={
                        "source": "orchestrator",
                        "error": "Summarization timeout after 5 seconds",
                        "stage": "summarization"
                    }
                )
            
            profiler.end_stage('summarization', f"{len(summary_output.result)} chars")
            
            if not summary_output.result or summary_output.confidence == 0.0:
                logger.error("❌ Summarization phase failed")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={
                        "source": "orchestrator",
                        "error": f"Summarization failed: {summary_output.metadata.get('error', 'Unknown')}",
                        "stage": "summarization"
                    }
                )
            
            logger.info(f"✅ STAGE 2 Complete: Summary confidence {summary_output.confidence:.2f}")
            
            # ============ STAGE 3: Semantic Validation ============
            profiler.start_stage('semantic_validation')
            logger.info("🔍 STAGE 3: Semantic validation...")
            is_coherent, coherence_adjustment = self._validate_summary_coherence(
                query, 
                summary_output.result,
                normalized_docs
            )
            
            if not is_coherent:
                logger.warning(f"⚠️ Summary may not be coherent with query/documents")
                # Don't fail, but penalize confidence
                summary_output.confidence *= 0.85
            
            adjusted_confidence = summary_output.confidence + coherence_adjustment * 0.1
            summary_output.confidence = min(1.0, adjusted_confidence)
            
            profiler.end_stage('semantic_validation', f"adjusted {summary_output.confidence:.2f}")
            logger.info(f"✅ STAGE 3 Complete: Adjusted confidence {summary_output.confidence:.2f}")
            
            # ============ STAGE 4: Review ============
            # 🎯 Fast mode optimization: Skip review stage (saves ~5-10s)
            if mode == "fast":
                logger.info("⚡ FAST MODE: Skipping review stage (saves 5-10s)")
                profiler.timings['review'] = {'duration': 0, 'skipped': True}
                final_output = summary_output
            else:
                profiler.start_stage('review')
                logger.info("✅ STAGE 4: Review phase starting...")
                review_input = AgentInput(
                    query=query,
                    context=summary_output.result,
                    metadata={"source": "orchestrator", "stage": "review", "mode": mode}  # 🎯 Pass mode to reviewer
                )
                
                # ⚡ Phase 1: Add timeout to review
                try:
                    final_output = await asyncio.wait_for(
                        self.reviewer.run(review_input, summary_output),
                        timeout=10.0  # 10 second timeout for review
                    )
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Review phase timeout - using summary output")
                    # Fallback to summary if review times out
                    final_output = summary_output
                profiler.end_stage('review', f"confidence {final_output.confidence:.2f}")

            # ⚡ Phase 1: Parallel post-processing (clustering, citations, memory)
            # 🎯 Fast mode optimization: Skip expensive post-processing (saves ~2-5s)
            if mode == "fast":
                logger.info("⚡ FAST MODE: Skipping post-processing (saves 2-5s)")
                profiler.timings['post_processing'] = {'duration': 0, 'skipped': True}
                clusters = []
                citations = []
            else:
                profiler.start_stage('post_processing')
                logger.info("🔀 STAGE 5: Parallel post-processing...")
                
                # Run independent operations concurrently
                cluster_task = asyncio.create_task(
                    asyncio.to_thread(self.clusterer.cluster, normalized_docs)
                )
                citation_task = asyncio.create_task(
                    asyncio.to_thread(self.citation_extractor.extract, normalized_docs)
                )
                memory_task = asyncio.create_task(
                    self.memory_store.remember(
                        query=query,
                        summary=final_output.result,
                        metadata={
                            "confidence": final_output.confidence,
                            "document_count": len(normalized_docs),
                        }
                    )
                )
                
                # Wait for all tasks to complete (with timeout)
                try:
                    clusters, citations, _ = await asyncio.wait_for(
                        asyncio.gather(cluster_task, citation_task, memory_task),
                        timeout=5.0  # 5 second timeout for post-processing
                    )
                    logger.info("✅ STAGE 5 Complete: Parallel processing finished")
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Post-processing timeout - using partial results")
                    # Use empty results if timeout
                    clusters = cluster_task.result() if cluster_task.done() else []
                    citations = citation_task.result() if citation_task.done() else []
                profiler.end_stage('post_processing', f"{len(clusters)} clusters, {len(citations)} citations")
            
            # Generate report (depends on clusters and citations)
            profiler.start_stage('report_generation')
            report_markdown = self.report_generator.generate(
                query=query,
                summary=final_output.result,
                clusters=clusters,
                citations=citations,
                confidence=final_output.confidence,
            )
            profiler.end_stage('report_generation')
            
            # Get performance summary
            perf_summary = profiler.get_summary()
            total_time = perf_summary['total_time']
            
            logger.info(f"\n{'='*80}")
            logger.info(f"✅ PIPELINE COMPLETE in {total_time:.2f}s")
            logger.info(f"📊 Final confidence: {final_output.confidence:.2f}")
            logger.info(f"\n⏱️  PERFORMANCE BREAKDOWN:")
            for stage, duration in perf_summary['breakdown'].items():
                percentage = (duration / total_time * 100) if total_time > 0 else 0
                logger.info(f"   • {stage}: {duration:.2f}s ({percentage:.1f}%)")
            logger.info(f"{'='*80}\n")
            
            # Ensure final output has proper metadata
            final_output.metadata.update({
                "sources": [doc["url"] for doc in normalized_docs if doc.get("url")],
                "documents": normalized_docs,  # 🎯 Phase 2: Store document objects for conversation caching
                "document_count": len(normalized_docs),
                "pipeline_stages": ["research", "summarization", "validation", "review"],
                "is_coherent": is_coherent,
                "plan": plan,
                "tool_selection": tool_selection,
                "clusters": clusters,
                "citations": citations,
                "report_markdown": report_markdown,
                "memory_hits": 0,  # 🔥 FIX: Set to 0 since we're using fresh memory store (not recalling old memories)
                "performance": {
                    "total_time": total_time,
                    "mode": mode,
                    "breakdown": perf_summary['breakdown'],
                    "profiling": perf_summary['detailed']
                }
            })
            
            return final_output
            
        except Exception as e:
            logger.error(f"❌ Critical error in pipeline: {str(e)}", exc_info=True)
            return AgentOutput(
                result="", 
                confidence=0.0, 
                metadata={
                    "source": "orchestrator",
                    "error": f"Pipeline error: {str(e)}",
                    "stage": "unknown"
                }
            )
    
    async def run_agentic_pipeline(
        self, 
        query: str, 
        max_results: int = 5,
        max_attempts: int = 3,
        mode: str = "thorough",  # 🎯 Phase 1: "fast" or "thorough"
        conversation_context: str = "",  # 🎯 Phase 2: Previous conversation context
        cached_papers: Optional[List[Dict]] = None  # 🎯 Phase 2: Pre-fetched papers from cache
    ) -> AgentOutput:
        """
        🎯 PHASE 2: Agentic AI Pipeline with Reasoning Loop + Conversation Memory
        
        This is the main entry point for the agentic system. It:
        1. Tries to fetch relevant documents (or uses cached papers for follow-ups)
        2. Evaluates result quality
        3. If quality is low, reformulates query and retries
        4. Uses exponential backoff between attempts
        5. Always includes Wikipedia results even with fallback
        6. 🎯 NEW: Uses conversation context for follow-up questions
        7. 🎯 NEW: Reuses cached papers for ~3s follow-up responses
        
        Args:
            query: User's original query
            max_results: Max papers to fetch per source
            max_attempts: Max retry attempts (default 3)
            mode: "fast" (chatbot, skip slow APIs) or "thorough" (research, all APIs)
            conversation_context: Previous conversation history for context
            cached_papers: Pre-fetched papers from session cache (for follow-ups)
            
        Returns:
            AgentOutput with final result and metadata including all attempts
        """
        if not self.data_fetcher:
            logger.error("❌ DataFetcher not available - cannot run agentic pipeline")
            return AgentOutput(
                result="",
                confidence=0.0,
                metadata={
                    "error": "DataFetcher not initialized",
                    "stage": "setup"
                }
            )
        
        logger.info("=" * 80)
        logger.info(f"🤖 AGENTIC PIPELINE STARTED ({mode.upper()} MODE)")
        logger.info(f"📝 Original Query: '{query}'")
        logger.info(f"🎯 Max Attempts: {max_attempts}")
        if mode == "fast":
            logger.info("⚡ FAST MODE: Skipping slow APIs (arXiv, OpenAlex), using only fast APIs")
        logger.info("=" * 80)
        
        # 🎯 Phase 1: Performance tracking
        pipeline_start_time = time.time()
        timing_breakdown = {
            'total': 0,
            'fetch': 0,
            'quality_eval': 0,
            'pipeline': 0
        }
        
        current_query = query
        attempt_history = []
        
        for attempt in range(max_attempts):
            logger.info("")
            logger.info(f"{'='*80}")
            logger.info(f"🔄 ATTEMPT {attempt + 1}/{max_attempts}")
            logger.info(f"{'='*80}")
            
            # Reformulate query if this is a retry
            if attempt > 0:
                current_query = self.query_rewriter.rewrite(query, attempt)
                logger.info(f"🔄 Query reformulated: '{current_query}'")
                
                # Exponential backoff: 1s, 2s, 4s
                backoff = 2 ** (attempt - 1)
                logger.info(f"⏳ Exponential backoff: waiting {backoff}s before retry...")
                await asyncio.sleep(backoff)
            
            # 🎯 Phase 2: Use cached papers for follow-ups (skip fetching)
            if cached_papers and len(cached_papers) > 0:
                logger.info(f"📦 Using {len(cached_papers)} cached papers from session (FOLLOW-UP MODE)")
                documents = cached_papers
                routing_info = {"reasoning": "Follow-up query using cached papers", "primary": "cache"}
                apis_used = ["session_cache"]
                fetch_time = 0.0
                timing_breakdown['fetch'] = 0.0
            else:
                # Fetch documents
                logger.info(f"📡 Fetching documents for: '{current_query}'")
                fetch_start = time.time()
                try:
                    # 🎯 Phase 3: Use smart routing instead of fetch_all
                    # 🎯 Phase 1: Pass mode to skip slow APIs in fast mode
                    fetch_result = await self.data_fetcher.fetch_with_smart_routing(
                        current_query,
                        max_results=max_results,
                        try_fallbacks=(attempt < max_attempts - 1),  # Only try fallbacks if not last attempt
                        mode=mode  # 🎯 Phase 1: "fast" skips arXiv/OpenAlex, "thorough" uses all
                    )
                    
                    documents = fetch_result["papers"]
                    routing_info = fetch_result["routing_info"]
                    apis_used = fetch_result["apis_used"]
                    
                    fetch_time = time.time() - fetch_start
                    timing_breakdown['fetch'] += fetch_time
                    
                    logger.info(f"✅ Fetched {len(documents)} documents from {apis_used} in {fetch_time:.2f}s")
                    logger.info(f"🧭 Routing: {routing_info['reasoning']}")
                except Exception as e:
                    fetch_time = time.time() - fetch_start
                    timing_breakdown['fetch'] += fetch_time
                    logger.error(f"❌ Fetch failed after {fetch_time:.2f}s: {e}")
                    documents = []
                    routing_info = {}
                    apis_used = []
            
            # Evaluate quality
            eval_start = time.time()
            decision, quality_score, reason = self.quality_evaluator.evaluate(
                query=current_query,
                documents=documents,
                attempt=attempt
            )
            timing_breakdown['quality_eval'] += time.time() - eval_start
            
            # Get source breakdown for accurate tracking
            source_breakdown = self.quality_evaluator._get_source_breakdown(documents)
            
            self.quality_evaluator.log_decision(decision, quality_score, reason)
            
            # Record this attempt
            attempt_history.append({
                "attempt": attempt + 1,
                "query": current_query,
                "document_count": len(documents),
                "quality_score": quality_score,
                "decision": decision,
                "reason": reason,
                "routing_info": routing_info,
                "apis_used": apis_used,
                "source_breakdown": source_breakdown  # 🎯 Phase 4: Track actual source counts
            })
            
            # Decision tree
            if decision == "continue":
                logger.info("✅ Quality acceptable - proceeding with pipeline")
                
                # 🎯 Phase 1: Time the pipeline execution
                pipeline_exec_start = time.time()
                result = await self.run_pipeline(current_query, documents, mode, conversation_context)
                timing_breakdown['pipeline'] = time.time() - pipeline_exec_start
                timing_breakdown['total'] = time.time() - pipeline_start_time
                
                # Add attempt history and performance metrics to metadata
                result.metadata["reasoning_attempts"] = attempt_history
                result.metadata["final_query"] = current_query
                result.metadata["original_query"] = query
                result.metadata["agentic_mode"] = True
                result.metadata["performance_breakdown"] = {
                    "total_time": round(timing_breakdown['total'], 2),
                    "fetch_time": round(timing_breakdown['fetch'], 2),
                    "quality_eval_time": round(timing_breakdown['quality_eval'], 3),
                    "pipeline_time": round(timing_breakdown['pipeline'], 2),
                    "attempts": attempt + 1
                }
                
                logger.info("=" * 80)
                logger.info("🎉 AGENTIC PIPELINE COMPLETE")
                logger.info(f"✅ Succeeded on attempt {attempt + 1}/{max_attempts}")
                logger.info(f"📊 Final Quality: {quality_score:.2f}")
                logger.info(f"⏱️  Performance: Total={timing_breakdown['total']:.2f}s, Fetch={timing_breakdown['fetch']:.2f}s, Pipeline={timing_breakdown['pipeline']:.2f}s")
                logger.info(f"🎯 Final Confidence: {result.confidence:.2f}")
                logger.info("=" * 80)
                
                return result
            
            elif decision == "retry":
                logger.info(f"🔄 Quality insufficient - will retry with attempt {attempt + 2}")
                continue
            
            else:  # give_up
                logger.warning("❌ Giving up - max retries or no hope of improvement")
                break
        
        # All attempts failed - return best effort result
        logger.warning("=" * 80)
        logger.warning("⚠️ ALL ATTEMPTS EXHAUSTED")
        logger.warning(f"❌ Failed to achieve quality threshold after {max_attempts} attempts")
        logger.warning("=" * 80)
        
        # Use last fetched documents (even if low quality)
        if documents:
            logger.info("📝 Using last attempt's documents as fallback...")
            result = await self.run_pipeline(current_query, documents, mode, conversation_context)
        else:
            logger.error("❌ No documents available - returning error")
            result = AgentOutput(
                result="Unable to fetch relevant research papers. Please try rephrasing your query or try again later.",
                confidence=0.0,
                metadata={
                    "error": "All fetch attempts failed",
                    "stage": "agentic_fetch"
                }
            )
        
        # Add failure metadata
        result.metadata["reasoning_attempts"] = attempt_history
        result.metadata["final_query"] = current_query
        result.metadata["original_query"] = query
        result.metadata["agentic_mode"] = True
        result.metadata["all_attempts_failed"] = True
        
        return result