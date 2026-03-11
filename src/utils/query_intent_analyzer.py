"""
Query Intent Analyzer - LLM-based query understanding and context extraction

Fixes hallucination issues by:
1. Understanding true query intent (e.g., "other animals" in cloning context = "cloning animals")
2. Extracting key concepts for better search
3. Determining if cached papers are relevant
"""
import logging
from typing import List, Dict, Optional
import os
from groq import Groq

logger = logging.getLogger(__name__)


class QueryIntentAnalyzer:
    """
    LLM-based query intent analyzer for better understanding and cache relevance.
    """
    
    def __init__(self):
        """Initialize with Groq API."""
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.1-8b-instant"
        logger.info("✅ QueryIntentAnalyzer initialized (Groq API)")
    
    def analyze_query_intent(
        self, 
        current_query: str, 
        conversation_history: List[str]
    ) -> Dict[str, any]:
        """
        Analyze query intent considering conversation context.
        
        Returns:
            {
                "is_follow_up": bool,
                "main_topic": str,
                "key_concepts": List[str],
                "search_query": str (reformulated for better search)
            }
        """
        try:
            # Build context from last 3 queries
            context = "\n".join([f"- {q}" for q in conversation_history[-3:]]) if conversation_history else "None"
            
            prompt = f"""Analyze this query in context and extract key information.

Previous conversation:
{context}

Current query: "{current_query}"

Determine:
1. Is this a follow-up to previous conversation or a NEW topic?
2. What is the MAIN topic/domain (e.g., climate, AI, biotech, cloning, technology)?
3. What are KEY CONCEPTS to search for (3-5 important keywords)?
4. Reformulated search query (expand abbreviations, add context, make specific)

Think step-by-step:
- If query says "leave this", "forget that", "new question" → NEW topic
- If query topic completely different from previous → NEW topic
- If query builds on previous context → FOLLOW-UP
- For ambiguous terms like "other animals", use conversation context (if talking about cloning → "cloning animals")

Respond in JSON format:
{{
    "is_follow_up": true/false,
    "main_topic": "topic name",
    "key_concepts": ["concept1", "concept2", "concept3"],
    "search_query": "reformulated query for search"
}}"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low temperature for consistent analysis
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            import json
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            logger.info(f"🎯 Intent: '{current_query}' → Topic: {result['main_topic']}, Follow-up: {result['is_follow_up']}")
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ Intent analysis failed: {e}, falling back to query as-is")
            # Fallback to basic analysis
            return {
                "is_follow_up": False,
                "main_topic": "general",
                "key_concepts": current_query.split()[:5],
                "search_query": current_query
            }
    
    def check_cache_relevance(
        self,
        query: str,
        query_intent: Dict[str, any],
        cached_paper_titles: List[str]
    ) -> float:
        """
        Check if cached papers are relevant to current query.
        
        Returns:
            Relevance score 0.0-1.0 (>0.6 = relevant, use cache; <0.6 = fetch new papers)
        """
        try:
            # If no cached papers, return 0
            if not cached_paper_titles:
                return 0.0
            
            # Sample up to 10 paper titles for analysis
            sample_titles = cached_paper_titles[:10]
            titles_text = "\n".join([f"- {t}" for t in sample_titles])
            
            prompt = f"""Rate the relevance of these research papers to the query.

Query: "{query}"
Main topic: {query_intent.get('main_topic', 'unknown')}
Key concepts: {', '.join(query_intent.get('key_concepts', []))}

Cached papers:
{titles_text}

Are these papers relevant to answer the query?
- If papers match the topic and could help answer → HIGH relevance (0.7-1.0)
- If papers are somewhat related but different focus → MEDIUM relevance (0.4-0.6)
- If papers are completely different topic → LOW relevance (0.0-0.3)

Example:
Query about "cloning animals" + papers about "Dolly sheep cloning" = HIGH (0.9)
Query about "cloning animals" + papers about "climate change" = LOW (0.1)
Query about "AI in biotech" + papers about "e-Books for students" = LOW (0.0)

Respond with ONLY a number between 0.0 and 1.0 (e.g., 0.85)"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=10
            )
            
            score_text = response.choices[0].message.content.strip()
            # Extract first number found
            import re
            match = re.search(r'0\.\d+|1\.0|0', score_text)
            if match:
                relevance_score = float(match.group())
                logger.info(f"📊 Cache relevance: {relevance_score:.2f} for query '{query[:50]}...'")
                return relevance_score
            else:
                logger.warning(f"⚠️ Could not parse relevance score: {score_text}")
                return 0.5  # Default to medium relevance
                
        except Exception as e:
            logger.warning(f"⚠️ Cache relevance check failed: {e}")
            return 0.5  # Default to medium relevance if check fails
    
    def validate_answer_relevance(
        self,
        query: str,
        answer: str,
        query_intent: Dict[str, any]
    ) -> Dict[str, any]:
        """
        🎯 POST-GENERATION VALIDATION: Check if answer actually matches query topic.
        
        Prevents hallucinations like answering "male dominance" query with "machine learning" content.
        
        Returns:
            {
                "is_relevant": bool,
                "confidence": float (0.0-1.0),
                "reason": str (why relevant/not relevant)
            }
        """
        try:
            main_topic = query_intent.get('main_topic', 'unknown')
            key_concepts = query_intent.get('key_concepts', [])
            
            # Extract first 500 chars of answer for validation
            answer_preview = answer[:500]
            
            prompt = f"""Validate if this answer is relevant to the query.

Query: "{query}"
Expected topic: {main_topic}
Expected concepts: {', '.join(key_concepts)}

Generated answer (first 500 chars):
"{answer_preview}"

CRITICAL CHECKS:
1. Does the answer address the query topic?
2. Does the answer contain concepts related to the query?
3. Is the answer on a completely different topic (hallucination)?

Examples of HALLUCINATIONS (answer is NOT relevant):
- Query: "male dominance in society" + Answer about "machine learning techniques" = NOT RELEVANT
- Query: "why philosophers are unhappy" + Answer about "computational methods" = NOT RELEVANT
- Query: "cloning animals" + Answer about "climate change" = NOT RELEVANT

Respond in JSON:
{{
    "is_relevant": true/false,
    "confidence": 0.0-1.0,
    "reason": "brief explanation"
}}"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON
            import json
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            is_relevant = result.get("is_relevant", True)
            confidence = result.get("confidence", 0.5)
            reason = result.get("reason", "Unknown")
            
            if is_relevant:
                logger.info(f"✅ Answer validation PASSED: {reason}")
            else:
                logger.warning(f"❌ Answer validation FAILED: {reason} - Will retry with fresh papers")
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ Answer validation failed: {e}, assuming answer is relevant")
            # On error, assume answer is relevant (fail-safe)
            return {
                "is_relevant": True,
                "confidence": 0.5,
                "reason": "Validation error, assuming relevant"
            }
