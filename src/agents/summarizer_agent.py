import logging
import asyncio
from .base import AgentInput, AgentOutput
import re
from typing import List, Tuple
from collections import Counter
import os

logger = logging.getLogger(__name__)

class SummarizerAgent:
    """
    LLM-based abstractive summarizer using Groq API (Cloud-hosted Llama).
    
    Performance: ~1-3s (GPU-accelerated cloud inference)
    Quality: Natural, coherent answers (better than local 3B)
    Memory: 0 (cloud API)
    Cost: FREE tier (30 req/min) or $0.10 per 1M tokens
    
    Strategy:
    1. Extract relevant context from research papers
    2. Synthesize coherent answer using Groq's Llama 3.1 8B
    3. Ground response in paper findings
    """
    
    def __init__(self):
        try:
            from groq import Groq
            
            # Initialize Groq client
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                logger.warning("⚠️ GROQ_API_KEY not set, will use fallback extractive summarization")
                self.client = None
            else:
                self.client = Groq(api_key=api_key)
                logger.info("✅ SummarizerAgent initialized with Groq API (llama-3.1-8b-instant)")
            
            # Model selection: Fast mode uses same model (Groq is already fast)
            self.model_name = "llama-3.1-8b-instant"  # ~1-3s inference
            
        except ImportError:
            logger.error("❌ Groq SDK not installed. Install: pip install groq")
            self.client = None

    async def run(self, input_data: AgentInput) -> AgentOutput:
        """
        LLM-based abstractive summarization using Groq API.
        Fast for both modes (~1-3s GPU inference).
        """
        # Extract mode from metadata (not used for Groq, but kept for compatibility)
        mode = input_data.metadata.get('mode', 'thorough') if input_data.metadata else 'thorough'
        
        logger.info(f"🔄 Running SummarizerAgent (Groq API, {mode.upper()} mode) with query: {input_data.query}")
        
        if not self.client:
            logger.error("❌ Groq API not available, falling back to extractive summarization")
            return self._fallback_extractive(input_data)
        
        try:
            context = input_data.context
            
            if not context or not isinstance(context, str):
                logger.warning("❌ No valid context provided")
                return AgentOutput(
                    result="",
                    confidence=0.0,
                    metadata={"source": "summarizer", "error": "Invalid context"}
                )
            
            # Validate minimum length
            if len(context.split()) < 20:
                logger.warning(f"⚠️ Context too short: {len(context.split())} words")
                return AgentOutput(
                    result=context[:500],
                    confidence=0.5,
                    metadata={"source": "summarizer", "warning": "Context too short"}
                )
            
            # Fast mode: shorter context + fewer tokens = faster Groq response
            is_fast = mode == 'fast'
            prompt = self._create_synthesis_prompt(input_data.query, context, fast=is_fast)
            max_tokens = 200 if is_fast else 400  # Shorter in fast mode
            groq_timeout = 8.0 if is_fast else 10.0  # Tighter timeout in fast mode
            
            # Call Groq API for synthesis (run in executor to avoid blocking event loop)
            logger.info(f"🧠 Calling Groq API ({self.model_name}) for synthesis ({mode} mode)...")
            import time
            start = time.time()
            
            # Use Groq's chat completion API (sync SDK, run in thread to avoid blocking)
            loop = asyncio.get_running_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a research assistant that synthesizes academic findings into clear, concise answers."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.7,
                        max_tokens=max_tokens,
                        top_p=0.9
                    )
                ),
                timeout=groq_timeout
            )
            
            elapsed = time.time() - start
            summary = response.choices[0].message.content.strip()
            
            # Validate output quality
            if len(summary) < 50:
                logger.warning(f"⚠️ LLM output too short ({len(summary)} chars), using fallback")
                return self._fallback_extractive(input_data)
            
            # Calculate confidence based on response quality
            confidence = self._calculate_confidence(summary, input_data.query)
            
            logger.info(f"✅ Groq summary generated: {len(summary)} chars in {elapsed:.2f}s (confidence: {confidence:.2f})")
            
            return AgentOutput(
                result=summary,
                confidence=confidence,
                metadata={
                    "source": "summarizer",
                    "method": "groq_api",
                    "model": self.model_name,
                    "time_ms": int(elapsed * 1000),
                    "response_length": len(summary)
                }
            )
            
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Groq API timeout (>10s), using extractive fallback")
            return self._fallback_extractive(input_data)
        except Exception as e:
            logger.error(f"❌ Error in Groq API summarizer: {str(e)}", exc_info=True)
            logger.info("⚠️ Falling back to extractive summarization")
            return self._fallback_extractive(input_data)
    
    def _create_synthesis_prompt(self, query: str, context: str, fast: bool = False) -> str:
        """Create prompt for LLM synthesis."""
        # Truncate context to keep prompts short and responses fast
        max_context_words = 300 if fast else 600
        context_words = context.split()
        if len(context_words) > max_context_words:
            context = ' '.join(context_words[:max_context_words]) + "..."
        
        if fast:
            prompt = f"""Synthesize the research findings below into a direct answer (80-120 words).

Question: {query}

Research:
{context}

IMPORTANT: If the research papers don't actually answer the question, respond with:
"I couldn't find relevant research papers for this specific query."

Answer concisely using "research shows", "studies found" etc:"""
        else:
            prompt = f"""You are a research assistant synthesizing findings from academic papers.

User Question: {query}

Research Findings:
{context}

Task: Write a clear, concise answer (150-200 words) that:
1. FIRST: Check if the research papers actually answer the user's question
2. If papers are IRRELEVANT or OFF-TOPIC, respond: "I couldn't find relevant research papers for this specific query."
3. If papers ARE relevant: Synthesize key findings into a natural answer
4. Use phrases like "research shows", "studies found" when citing findings
5. Be honest about limitations - don't fabricate connections between query and papers

CRITICAL: Do NOT make up connections. If papers don't match the query, admit it.

Answer:"""
        
        return prompt
    
    def _calculate_confidence(self, summary: str, query: str) -> float:
        """Calculate confidence score for LLM output."""
        # Check if LLM admitted no relevant papers found
        no_results_phrases = [
            "couldn't find relevant",
            "no relevant research",
            "papers don't match",
            "not relevant to",
            "off-topic"
        ]
        
        if any(phrase in summary.lower() for phrase in no_results_phrases):
            logger.info("⚠️ LLM detected irrelevant papers - returning low confidence")
            return 0.3  # Low confidence when papers are irrelevant
        
        # Basic heuristics for confidence
        query_words = set(query.lower().split())
        summary_words = set(summary.lower().split())
        
        # Keyword overlap
        overlap = len(query_words & summary_words) / max(len(query_words), 1)
        
        # Length check (prefer 100-300 words)
        word_count = len(summary.split())
        if 100 <= word_count <= 300:
            length_score = 1.0
        elif word_count < 100:
            length_score = word_count / 100
        else:
            length_score = max(0.5, 1.0 - (word_count - 300) / 500)
        
        # Check for hedging phrases (lower confidence)
        hedging = ['may', 'might', 'possibly', 'unclear', 'limited research']
        hedge_count = sum(1 for word in hedging if word in summary.lower())
        hedge_penalty = min(0.2, hedge_count * 0.05)
        
        confidence = min(0.95, 0.6 + overlap * 0.2 + length_score * 0.15 - hedge_penalty)
        return confidence
    
    def _fallback_extractive(self, input_data: AgentInput) -> AgentOutput:
        """Fallback to simple extractive summarization if LLM fails."""
        logger.info("📝 Using fallback extractive summarization")
        
        context = input_data.context
        sentences = context.split('. ')[:5]  # Take first 5 sentences
        summary = '. '.join(sentences)
        if not summary.endswith('.'):
            summary += '.'
        
        return AgentOutput(
            result=summary,
            confidence=0.5,
            metadata={
                "source": "summarizer",
                "method": "extractive_fallback",
                "warning": "LLM unavailable"
            }
        )