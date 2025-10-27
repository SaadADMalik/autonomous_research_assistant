import logging
from typing import List, Union
from src.agents.researcher_agent import ResearcherAgent
from src.agents.summarizer_agent import SummarizerAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.utils.logger import setup_logging
from src.agents.base import AgentInput, AgentOutput
from difflib import SequenceMatcher

setup_logging()
logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        logger.info("🚀 Initializing Orchestrator")
        try:
            self.researcher = ResearcherAgent()
            self.summarizer = SummarizerAgent()
            self.reviewer = ReviewerAgent()
            logger.info("✅ All agents initialized successfully")
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

    async def run_pipeline(self, query: str, documents: List[Union[dict, str]]) -> AgentOutput:
        logger.info(f"🔄 Running pipeline with query: '{query}'")
        
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
            
            # ============ STAGE 1: Research ============
            logger.info("📖 STAGE 1: Research phase starting...")
            research_input = AgentInput(
                query=query, 
                metadata={"source": "orchestrator", "stage": "research"}
            )
            
            research_output = await self.researcher.run(research_input, normalized_docs)
            
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
            
            logger.info(f"✅ STAGE 1 Complete: Research confidence {research_output.confidence:.2f}")
            
            # ============ STAGE 2: Summarization ============
            logger.info("📝 STAGE 2: Summarization phase starting...")
            summary_input = AgentInput(
                query=query,
                context=research_output.result,
                metadata={"source": "orchestrator", "stage": "summarization"}
            )
            
            summary_output = await self.summarizer.run(summary_input)
            
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
            
            logger.info(f"✅ STAGE 3 Complete: Adjusted confidence {summary_output.confidence:.2f}")
            
            # ============ STAGE 4: Review ============
            logger.info("✅ STAGE 4: Review phase starting...")
            review_input = AgentInput(
                query=query,
                context=summary_output.result,
                metadata={"source": "orchestrator", "stage": "review"}
            )
            
            final_output = await self.reviewer.run(review_input, summary_output)
            
            # Ensure final output has proper metadata
            final_output.metadata.update({
                "source": "orchestrator",
                "sources": [doc["url"] for doc in normalized_docs if doc.get("url")],
                "document_count": len(normalized_docs),
                "pipeline_stages": ["research", "summarization", "validation", "review"],
                "is_coherent": is_coherent
            })
            
            logger.info(f"✅ PIPELINE COMPLETE: Final confidence {final_output.confidence:.2f}")
            logger.info(f"📊 Output summary: {final_output.result[:80]}...")
            
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