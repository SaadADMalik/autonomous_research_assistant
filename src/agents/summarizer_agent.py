import logging
from .base import AgentInput, AgentOutput
from transformers import pipeline
import torch
import re

logger = logging.getLogger(__name__)

class SummarizerAgent:
    def __init__(self):
        logger.info("Initializing SummarizerAgent with BART model")
        self.device = 0 if torch.cuda.is_available() else -1  # Use GPU if available, else CPU
        try:
            self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn", device=self.device)
            logger.info("✅ BART model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load BART model: {str(e)}")
            self.summarizer = None

    def _validate_context(self, context: str) -> str:
        """Validate and clean context for summarization."""
        if not context or not isinstance(context, str):
            logger.warning("⚠️ Invalid context: not a string or empty")
            return ""
        
        # Clean up whitespace
        context = context.strip()
        context = re.sub(r'\s+', ' ', context)  # Normalize whitespace
        
        # Minimum context length for BART (need at least 50 tokens)
        min_tokens = 50
        token_count = len(context.split())
        
        if token_count < min_tokens:
            logger.warning(f"⚠️ Context too short: {token_count} tokens (need {min_tokens})")
            return ""
        
        logger.debug(f"✅ Context validated: {token_count} tokens")
        return context

    async def run(self, input_data: AgentInput) -> AgentOutput:
        logger.info(f"🔄 Running SummarizerAgent with query: {input_data.query}")
        try:
            # Validate context
            context = self._validate_context(input_data.context)
            
            if not context:
                logger.warning("❌ No valid context provided for summarization")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={
                        "source": "summarizer",
                        "error": "Invalid or insufficient context",
                        "query": input_data.query
                    }
                )
            
            if not self.summarizer:
                logger.error("❌ BART model not initialized")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={
                        "source": "summarizer",
                        "error": "Summarization model unavailable"
                    }
                )
            
            # Calculate dynamic length parameters
            input_length = len(context.split())
            max_length = min(150, max(50, input_length // 3))  # 1/3 of input or 50-150
            min_length = min(40, max(20, input_length // 6))   # 1/6 of input or 20-40
            
            logger.debug(f"📊 Summarization params: max_length={max_length}, min_length={min_length}")
            
            try:
                # Run summarization with error handling
                summary_result = self.summarizer(
                    context,
                    max_length=max_length,
                    min_length=min_length,
                    do_sample=False
                )
                
                if not summary_result or not summary_result[0]:
                    logger.error("❌ Summarizer returned empty result")
                    return AgentOutput(
                        result="", 
                        confidence=0.0, 
                        metadata={
                            "source": "summarizer",
                            "error": "Summarizer returned empty"
                        }
                    )
                
                summary = summary_result[0]['summary_text'].strip()
                confidence = 0.92  # High confidence for BART-generated summaries
                
                logger.info(f"✅ Summary generated: {summary[:60]}... (confidence: {confidence:.2f})")
                
                return AgentOutput(
                    result=summary,
                    confidence=confidence,
                    metadata={
                        "source": "summarizer",
                        "input_tokens": input_length,
                        "model": "facebook/bart-large-cnn",
                        "query": input_data.query
                    }
                )
                
            except RuntimeError as e:
                logger.error(f"❌ BART Runtime Error: {str(e)}")
                # Fallback: Extract first meaningful sentences
                return AgentOutput(
                    result=self._extractive_fallback(context, max_length),
                    confidence=0.65,
                    metadata={
                        "source": "summarizer",
                        "method": "extractive_fallback",
                        "error": f"BART failed: {str(e)}"
                    }
                )
            
        except Exception as e:
            logger.error(f"❌ Critical error in SummarizerAgent: {str(e)}", exc_info=True)
            return AgentOutput(
                result="", 
                confidence=0.0, 
                metadata={
                    "source": "summarizer",
                    "error": f"Unexpected error: {str(e)}"
                }
            )

    def _extractive_fallback(self, context: str, max_length: int) -> str:
        """Simple extractive summarization fallback when BART fails."""
        try:
            if not context or len(context.strip()) < 10:
                logger.warning("[FALLBACK] Context too short for fallback")
                return ""
            
            # Split into sentences
            sentences = re.split(r'[.!?]+', context)
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
            
            if not sentences:
                # If no sentences, just return first part of context
                logger.info("[FALLBACK] No sentences found, using truncated context as summary")
                return context[:300].strip()
            
            # Take first N sentences that fit max_length tokens
            summary_sentences = []
            token_count = 0
            
            for sentence in sentences[:5]:  # Max 5 sentences
                sentence_tokens = len(sentence.split())
                if token_count + sentence_tokens <= max_length * 1.5:  # Allow some flexibility
                    summary_sentences.append(sentence.strip() + ".")
                    token_count += sentence_tokens
                else:
                    break
            
            if summary_sentences:
                fallback = " ".join(summary_sentences)
                logger.info(f"[FALLBACK] Extractive summary: {fallback[:60]}...")
                return fallback
            else:
                # If no sentences fit, use truncated context
                logger.info("[FALLBACK] Returning truncated context")
                return context[:300].strip()
            
        except Exception as e:
            logger.error(f"[FALLBACK] Extractive fallback failed: {str(e)}")
            # Ultimate fallback: return first 300 chars
            return context[:300].strip() if context else ""