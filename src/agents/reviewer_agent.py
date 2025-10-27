import logging
from .base import AgentInput, AgentOutput
from .summarizer_agent import SummarizerAgent
import re

logger = logging.getLogger(__name__)

class ReviewerAgent:
    def __init__(self, confidence_threshold: float = 0.75):
        logger.info(f"🔍 Initializing ReviewerAgent (threshold: {confidence_threshold})")
        self.confidence_threshold = confidence_threshold
        self.summarizer = SummarizerAgent()

    def _check_summary_length(self, summary: str) -> bool:
        """Ensure summary is reasonable length (not too short)."""
        if not summary:
            return False
        
        word_count = len(summary.split())
        min_words = 20
        max_words = 500
        
        is_valid = min_words <= word_count <= max_words
        logger.debug(f"📏 Summary length: {word_count} words (valid: {is_valid})")
        
        return is_valid

    def _extract_key_entities(self, text: str) -> set:
        """Extract important entities (proper nouns, specific terms)."""
        if not text:
            return set()
        
        # Match capitalized words (simple entity extraction)
        entities = set(re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b', text))
        logger.debug(f"🏷️ Extracted {len(entities)} key entities")
        
        return entities

    async def run(self, input_data: AgentInput, previous_output: AgentOutput = None) -> AgentOutput:
        logger.info(f"🔍 Running ReviewerAgent with query: {input_data.query}")
        
        try:
            if not input_data.context or not input_data.context.strip():
                logger.warning("⚠️ No context provided for review")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={
                        "source": "reviewer",
                        "error": "No context",
                        "stage": "validation"
                    }
                )
            
            result = input_data.context.strip()
            base_confidence = previous_output.confidence if (previous_output and previous_output.confidence) else 0.7
            
            # ===== Validation Checks =====
            
            # Check 1: Summary length
            if not self._check_summary_length(result):
                logger.warning(f"⚠️ Summary length validation failed")
                confidence = base_confidence * 0.8
            else:
                confidence = base_confidence
            
            # Check 2: Keyword presence from query
            query_words = set(input_data.query.lower().split())
            summary_words = set(result.lower().split())
            
            common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be', 'been', 'of', 'to', 'in', 'for', 'on', 'with', 'by', 'from', 'at', 'as', 'it', 'that', 'this'}
            query_words -= common_words
            summary_words -= common_words
            
            keyword_match = len(query_words & summary_words) / max(len(query_words), 1)
            logger.debug(f"🔑 Keyword match: {keyword_match:.2f}")
            
            if keyword_match < 0.15:
                logger.warning(f"⚠️ Low keyword match: {keyword_match:.2f}")
                confidence *= 0.85
            
            # Check 3: Entity extraction
            query_entities = self._extract_key_entities(input_data.query)
            summary_entities = self._extract_key_entities(result)
            
            if query_entities:
                entity_match = len(query_entities & summary_entities) / len(query_entities)
                logger.debug(f"🏷️ Entity match: {entity_match:.2f}")
                confidence = confidence * (0.95 + entity_match * 0.05)
            
            # ===== Confidence Assessment =====
            
            if confidence < self.confidence_threshold:
                logger.warning(f"⚠️ Confidence {confidence:.2f} below threshold {self.confidence_threshold}")
                logger.info(f"📝 Attempting to re-summarize with adjusted query...")
                
                try:
                    # Retry with more specific prompt
                    adjusted_input = AgentInput(
                        query=input_data.query + " (Focus on key findings and methodology)",
                        context=input_data.context,
                        metadata={**input_data.metadata, "retry": True}
                    )
                    
                    retry_output = await self.summarizer.run(adjusted_input)
                    
                    if retry_output.confidence > 0.0 and retry_output.result:
                        logger.info(f"✅ Retry successful: {retry_output.result[:50]}...")
                        result = retry_output.result
                        confidence = retry_output.confidence * 0.9  # Slightly penalize retry
                    else:
                        logger.warning(f"⚠️ Retry failed, using original summary")
                        
                except Exception as e:
                    logger.error(f"❌ Error during retry: {str(e)}")
                    # Continue with original summary
            
            # Final confidence cap
            final_confidence = min(0.95, max(0.3, confidence))
            
            logger.info(f"✅ Review complete: confidence {final_confidence:.2f}, summary length {len(result.split())} words")
            
            return AgentOutput(
                result=result,
                confidence=final_confidence,
                metadata={
                    "source": "reviewer",
                    "keyword_match": keyword_match,
                    "entity_match": len(query_entities & summary_entities) if query_entities else 0,
                    "validation_passed": confidence >= self.confidence_threshold,
                    "retry": confidence < self.confidence_threshold
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Error in ReviewerAgent: {str(e)}", exc_info=True)
            return AgentOutput(
                result="", 
                confidence=0.0, 
                metadata={
                    "source": "reviewer",
                    "error": f"Review failed: {str(e)}"
                }
            )