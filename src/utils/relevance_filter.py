"""
Relevance filter to remove irrelevant papers before processing.
Prevents contamination from papers that match keywords out of context.
"""
import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)


class RelevanceFilter:
    """Filter out papers that are clearly irrelevant to the query."""
    
    # Terms that should EXCLUDE a paper if they're dominant themes
    NEGATIVE_INDICATORS = {
        "rape": ["rape", "rapist", "sexual violence", "sexual assault", "convicted"],
        "crime": ["prison", "incarcerated", "criminal", "convicted", "offender", "inmate"],
        "death": ["suicide", "mortality", "death", "dying", "deceased"],
        "disease_primary": ["cancer treatment", "chemotherapy", "tumor", "carcinoma", "malignant"],
        "war": ["military conflict", "warfare", "combat", "battlefield"]
    }
    
    def filter_papers(self, query: str, papers: List[Dict]) -> List[Dict]:
        """
        Filter papers to keep only those relevant to the query.
        
        Args:
            query: Original search query
            papers: List of paper dictionaries from APIs
            
        Returns:
            Filtered list of papers
        """
        if not papers:
            return papers
        
        query_lower = query.lower()
        filtered = []
        removed_count = 0
        
        for paper in papers:
            if self._is_relevant(query_lower, paper):
                filtered.append(paper)
            else:
                removed_count += 1
                logger.warning(f"🚫 Filtered out irrelevant paper: {paper.get('title', 'Unknown')[:80]}")
        
        if removed_count > 0:
            logger.info(f"✅ Relevance Filter: Kept {len(filtered)}/{len(papers)} papers (removed {removed_count} irrelevant)")
        
        return filtered
    
    def _is_relevant(self, query_lower: str, paper: Dict) -> bool:
        """
        Check if a paper is relevant to the query.
        
        Returns:
            True if relevant, False if should be filtered out
        """
        title = (paper.get('title') or '').lower()
        abstract = (paper.get('summary') or '').lower()[:500]  # First 500 chars of abstract
        content = f"{title} {abstract}"
        
        # Check if abstract is actually a table of contents (many colons, short phrases)
        if self._is_table_of_contents(paper.get('summary') or ''):
            logger.debug(f"Paper rejected: Abstract appears to be table of contents")
            return False
        
        # Check for negative indicators that are dominant
        for category, negative_terms in self.NEGATIVE_INDICATORS.items():
            # Count how many negative terms appear
            negative_matches = sum(1 for term in negative_terms if term in content)
            
            # If 2+ negative terms from same category appear, likely off-topic
            if negative_matches >= 2:
                # Special case: if query explicitly asks about this topic, allow it
                if any(term in query_lower for term in negative_terms):
                    continue  # Query is about this topic, so it's relevant
                
                logger.debug(f"Paper rejected: {negative_matches} matches for {category}")
                return False
        
        # Check for "careers in crime" vs "careers for women"
        if "career" in query_lower and "women" in query_lower:
            # Reject if "career" appears with crime-related terms
            if re.search(r'\bcareer[s]?\s+(in|of)\s+(crime|criminal)', content, re.IGNORECASE):
                logger.debug("Paper rejected: 'careers in crime' not relevant to 'careers for women'")
                return False
        
        # Paper passed all filters
        return True
    
    def _is_table_of_contents(self, text: str) -> bool:
        """
        Detect if text is a table of contents rather than an abstract.
        TOCs have many colons and short phrases.
        """
        if not text or len(text) < 100:
            return False
        
        # Count colons per 100 characters
        colon_density = text.count(':') / (len(text) / 100)
        
        # If more than 3-4 colons per 100 chars, likely a TOC
        if colon_density > 3:
            return True
        
        # Check for TOC patterns: "Chapter X:", "Section Y:", numbered lists
        toc_patterns = [
            r'\b(chapter|section|part|appendix)\s+\d+:',
            r'^\d+\.\s+[A-Z]',  # "1. Introduction"
            r':\s+[A-Z][^.]{10,50}:',  # "Topic: Subtopic: Another:"
        ]
        
        for pattern in toc_patterns:
            if re.search(pattern, text[:500], re.MULTILINE | re.IGNORECASE):
                return True
        
        return False
