"""
Quality Evaluator Agent - Assesses search result quality and decides retry strategy.

This agent evaluates whether fetched papers are relevant to the query
and determines if the system should retry with a reformulated query.
"""

import logging
from typing import Dict, List, Tuple
from .base import AgentInput, AgentOutput

logger = logging.getLogger(__name__)


class QualityEvaluatorAgent:
    """
    Evaluates search result quality and determines retry strategy.
    
    Signals:
    - "continue": Results are good, proceed with pipeline
    - "retry": Results are poor, reformulate query and retry
    - "give_up": Max retries reached or no hope of improvement
    
    Quality Factors:
    1. Number of papers retrieved (0 = instant retry)
    2. Source quality (Semantic Scholar > Wikipedia > Educational fallback)
    3. Relevance (basic keyword matching for now, embeddings later)
    """
    
    # Quality thresholds
    MIN_PAPERS_GOOD = 5  # Need at least 5 papers for good quality
    MIN_PAPERS_ACCEPTABLE = 2  # Minimum 2 papers to proceed
    QUALITY_THRESHOLD = 0.6  # Quality score must be >= 0.6 to continue
    
    # Source scores
    SEMANTIC_SCHOLAR_SCORE = 3.0
    WIKIPEDIA_SCORE = 1.5
    EDUCATIONAL_FALLBACK_SCORE = 0.5
    
    def __init__(self):
        logger.info("✅ QualityEvaluatorAgent initialized")
    
    def evaluate(
        self,
        query: str,
        documents: List[dict],
        attempt: int
    ) -> Tuple[str, float, str]:
        """
        Evaluate search result quality.
        
        Args:
            query: The search query used
            documents: List of fetched documents
            attempt: Current attempt number (0, 1, 2)
            
        Returns:
            Tuple of (decision, quality_score, reason)
            - decision: "continue" | "retry" | "give_up"
            - quality_score: Float 0.0-1.0
            - reason: Human-readable explanation
        """
        # Edge case: No documents
        if not documents:
            if attempt >= 2:
                return "give_up", 0.0, "No documents after 3 attempts"
            return "retry", 0.0, "Zero documents retrieved"
        
        # Calculate quality score
        quality_score = self._calculate_quality(query, documents)
        
        logger.info(f"📊 Quality Evaluation (Attempt {attempt})")
        logger.info(f"   Papers: {len(documents)}")
        logger.info(f"   Quality Score: {quality_score:.2f}/1.0")
        
        # Decision logic
        if quality_score >= self.QUALITY_THRESHOLD:
            return "continue", quality_score, "Quality threshold met"
        
        if len(documents) < self.MIN_PAPERS_ACCEPTABLE:
            if attempt >= 2:
                return "give_up", quality_score, "Insufficient papers after max retries"
            return "retry", quality_score, f"Only {len(documents)} papers found"
        
        # Check if retrying might help
        if attempt >= 2:
            return "give_up", quality_score, "Max retries reached"
        
        # Low quality but might improve with reformulation
        source_breakdown = self._get_source_breakdown(documents)
        real_research_papers = (source_breakdown.get("arxiv", 0) + 
                                source_breakdown.get("openalex", 0) + 
                                source_breakdown.get("semantic_scholar", 0))
        educational_papers = source_breakdown.get("educational", 0)
        
        # Only retry if educational fallback dominates AND we have few real papers
        if educational_papers > real_research_papers and real_research_papers <3:
            return "retry", quality_score, f"Too many educational fallback results ({educational_papers} educational vs {real_research_papers} real)"
        
        if quality_score < 0.4:
            return "retry", quality_score, "Quality score too low"
        
        # Borderline quality - acceptable but not great
        return "continue", quality_score, "Acceptable quality (borderline)"
    
    def _calculate_quality(self, query: str, documents: List[dict]) -> float:
        """
        Calculate quality score 0.0-1.0 based on multiple factors.
        
        Scoring:
        - Source quality: 50% weight
        - Number of papers: 30% weight
        - Relevance: 20% weight
        """
        if not documents:
            return 0.0
        
        # 1. Source quality (50% weight)
        source_score = self._score_sources(documents)
        
        # 2. Document count (30% weight)
        count_score = min(len(documents) / 10.0, 1.0)  # 10+ papers = perfect score
        
        # 3. Relevance (20% weight) - basic keyword matching
        relevance_score = self._score_relevance(query, documents)
        
        # Weighted average
        final_score = (source_score * 0.5) + (count_score * 0.3) + (relevance_score * 0.2)
        
        logger.debug(f"   Source: {source_score:.2f}, Count: {count_score:.2f}, Relevance: {relevance_score:.2f}")
        
        return min(final_score, 1.0)
    
    def _score_sources(self, documents: List[dict]) -> float:
        """
        Score based on document sources.
        
        🎯 Phase 3: Updated to recognize arXiv and OpenAlex as high-quality sources
        
        Returns normalized score 0.0-1.0
        """
        total_score = 0.0
        
        for doc in documents:
            source = doc.get("source", "unknown").lower()
            
            # High quality academic sources (arXiv, OpenAlex, Semantic Scholar)
            if any(api in source for api in ["arxiv", "openalex", "semantic_scholar"]):
                total_score += self.SEMANTIC_SCHOLAR_SCORE  # 3.0 points
            elif "wikipedia" in source:
                total_score += self.WIKIPEDIA_SCORE  # 1.5 points
            else:  # Educational fallback
                total_score += self.EDUCATIONAL_FALLBACK_SCORE  # 0.5 points
        
        # Normalize: assume 7 quality papers = perfect (21 points)
        max_possible = self.SEMANTIC_SCHOLAR_SCORE * 7
        return min(total_score / max_possible, 1.0)
    
    def _score_relevance(self, query: str, documents: List[dict]) -> float:
        """
        Basic relevance scoring using keyword overlap.
        
        TODO: Use embeddings for semantic similarity in future
        """
        query_keywords = set(query.lower().split())
        
        if not query_keywords:
            return 0.5  # Neutral score
        
        relevance_scores = []
        
        for doc in documents:
            title = doc.get("title", "").lower()
            abstract = doc.get("abstract", "").lower()
            content = f"{title} {abstract}"
            
            # Count keyword overlaps
            overlaps = sum(1 for kw in query_keywords if kw in content)
            relevance = overlaps / len(query_keywords)
            relevance_scores.append(relevance)
        
        # Average relevance across all documents
        return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    
    def _get_source_breakdown(self, documents: List[dict]) -> Dict[str, int]:
        """
        Get count of documents by source type.
        
        🎯 Phase 3: Updated to track arXiv, OpenAlex, Semantic Scholar separately
        """
        breakdown = {
            "arxiv": 0,
            "openalex": 0,
            "semantic_scholar": 0,
            "wikipedia": 0,
            "educational": 0
        }
        
        for doc in documents:
            source = doc.get("source", "unknown").lower()
            
            if "arxiv" in source:
                breakdown["arxiv"] += 1
            elif "openalex" in source:
                breakdown["openalex"] += 1
            elif "semantic_scholar" in source:
                breakdown["semantic_scholar"] += 1
            elif "wikipedia" in source:
                breakdown["wikipedia"] += 1
            else:
                breakdown["educational"] += 1
        
        return breakdown
    
    def log_decision(self, decision: str, quality_score: float, reason: str):
        """Pretty-print the decision for logging."""
        emoji = {
            "continue": "✅",
            "retry": "🔄",
            "give_up": "❌"
        }
        
        logger.info(f"{emoji.get(decision, '❓')} Decision: {decision.upper()}")
        logger.info(f"   Quality: {quality_score:.2f}/1.0")
        logger.info(f"   Reason: {reason}")
