"""
Query Rewriter Agent - Reformulates user queries for better academic search results.

This agent transforms colloquial/casual queries into academic search terms
and provides alternative formulations when initial searches fail.
"""

import logging
from typing import List
from .base import AgentInput, AgentOutput

logger = logging.getLogger(__name__)


class QueryRewriterAgent:
    """
    Reformulates queries for academic search optimization.
    
    Strategy:
    - Attempt 0: Expand casual language to academic terms
    - Attempt 1: Add domain synonyms and related concepts
    - Attempt 2: Broaden to core concepts (remove specifics)
    """
    
    # Casual to academic transformations
    # Order matters! More specific patterns first to avoid partial replacements
    TRANSFORMATIONS = {
        "why": "factors contributing to",
        "how": "mechanisms of",
        "what causes": "etiology of",
        "what is": "overview of",
        "explain": "analysis of",
        # Gender terms - use word boundaries to avoid replacing "men" inside "women"
        "\bmen\b": "male",
        "\bwomen\b": "female",
        "\bman\b": "male",
        "\bwoman\b": "female",
        # Health/mental health terms - preserve key subject terms
        "suicide": "suicide",
        "suicidal": "suicidal",
        "suicides": "suicides",
        # Comparison terms - don't over-expand, keep queries focused
        "more": "higher",
        "less": "lower",
        "better": "improved",
        "worse": "reduced",
    }
    
    # Domain-specific synonyms for query expansion
    SYNONYMS = {
        # Technology
        "AI": ["artificial intelligence", "machine learning", "deep learning", "neural networks"],
        "quantum computing": ["quantum computation", "quantum algorithms", "qubits", "quantum gates"],
        "blockchain": ["distributed ledger", "cryptocurrency", "decentralized"],
        
        # Healthcare
        "healthcare": ["medical", "clinical", "health services", "patient care"],
        "disease": ["pathology", "disorder", "syndrome", "condition"],
        "treatment": ["therapy", "intervention", "therapeutic approach"],
        "diagnosis": ["diagnostic", "detection", "screening"],
        
        # Science
        "climate change": ["global warming", "climate crisis", "environmental change", "greenhouse effect"],
        "gene editing": ["CRISPR", "genetic modification", "genome editing"],
        "renewable energy": ["sustainable energy", "clean energy", "alternative energy"],
        
        # Social Sciences & Mental Health
        "mental health": ["psychological wellbeing", "psychiatric", "mental illness"],
        "suicide": ["suicidal behavior", "self-harm", "suicide prevention", "suicide risk"],
        "depression": ["depressive disorder", "major depression", "clinical depression"],
        "education": ["learning", "pedagogy", "academic", "instruction"],
        "economy": ["economic", "financial", "market"],
    }
    
    # Common stop words to potentially remove in attempt 2
    STOPWORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'should', 'could', 'may', 'might', 'must', 'can'
    }
    
    def __init__(self):
        logger.info("✅ QueryRewriterAgent initialized")
    
    def _is_question(self, query: str) -> bool:
        """Check if query is a question."""
        query_lower = query.lower().strip()
        question_words = ['how', 'why', 'what', 'when', 'where', 'which', 'who', 'whom', 'whose', 'does', 'do', 'did', 'is', 'are', 'was', 'were', 'can', 'could', 'will', 'would', 'should']
        return (query.endswith('?') or 
                any(query_lower.startswith(qw + ' ') for qw in question_words))
    
    def _question_to_statement(self, query: str) -> str:
        """
        🤖 Convert questions to statement form for better API search.
        
        Examples:
        - "how being a mother changes a female" → "motherhood changes women maternal brain development postpartum"
        - "why men commit more suicides than women" → "male suicide rates gender differences suicide methods"
        - "what causes climate change" → "climate change causes greenhouse gases carbon emissions"
        """
        query_lower = query.lower().strip('?').strip()
        
        # Remove question prefixes
        for prefix in ['how does', 'how do', 'how is', 'how are', 'how', 
                       'why does', 'why do', 'why is', 'why are', 'why',
                       'what causes', 'what is', 'what are', 'what',
                       'when does', 'when do', 'when',
                       'where does', 'where do', 'where',
                       'which', 'who', 'whom']:
            if query_lower.startswith(prefix + ' '):
                query_lower = query_lower[len(prefix):].strip()
                break
        
        # Remove auxiliary verbs that make it a question
        query_lower = query_lower.replace(' does ', ' ').replace(' do ', ' ')
        query_lower = query_lower.replace(' is ', ' ').replace(' are ', ' ')
        query_lower = query_lower.replace(' being ', ' ')
        
        # Domain-specific reformulations for common question patterns
        reformulations = {
            "mother changes female": "motherhood maternal changes women postpartum brain development",
            "mother changes women": "motherhood maternal changes women postpartum brain development",
            "men commit more suicides": "male suicide rates gender differences methods",
            "women commit more suicides": "female suicide rates gender differences methods",
            "climate change": "climate change causes effects solutions",
            "quantum computing": "quantum computing applications algorithms qubits",
        }
        
        # Check for pattern matches
        for pattern, replacement in reformulations.items():
            if pattern in query_lower:
                logger.info(f"🎯 Question reformulated: '{query}' → '{replacement}'")
                return replacement
        
        # Generic fallback: keep core nouns and verbs
        logger.info(f"🎯 Question simplified: '{query}' → '{query_lower}'")
        return query_lower
    
    def rewrite(self, query: str, attempt: int = 0) -> str:
        """
        🎯 Phase 4: Adaptive query rewriting based on length.
        
        Strategy by query length:
        - Short (1-3 words): Expand aggressively with synonyms
        - Medium (4-10 words): Apply standard transformations
        - Long (11+ words): Extract key concepts to focus search
        
        Args:
            query: Original user query
            attempt: Retry attempt number (0, 1, or 2)
            
        Returns:
            Reformulated query string
        """
        # 🤖 NEW: Preprocess questions to statement form for better API search
        if attempt == 0 and self._is_question(query):
            query = self._question_to_statement(query)
            logger.info(f"🎯 Question detected and reformulated")
        
        word_count = len(query.split())
        
        # 🎯 Phase 4: Adaptive processing based on query length
        if word_count <= 3:
            # Short queries: Expand aggressively
            if attempt == 0:
                rewritten = self._add_synonyms(query)  # Add synonyms immediately
                logger.info(f"📝 Short query ({word_count} words), Attempt {attempt}: Aggressive expansion")
            elif attempt == 1:
                rewritten = self._expand_keywords(self._add_synonyms(query))  # Stack expansion + synonyms
                logger.info(f"📝 Short query ({word_count} words), Attempt {attempt}: Double expansion")
            else:
                rewritten = query  # Last resort: use original
                logger.info(f"📝 Short query ({word_count} words), Attempt {attempt}: Using original")
        
        elif word_count <= 10:
            # Medium queries: Standard processing
            if attempt == 0:
                rewritten = self._expand_keywords(query)
                logger.info(f"📝 Medium query ({word_count} words), Attempt {attempt}: Keyword expansion")
            elif attempt == 1:
                rewritten = self._add_synonyms(query)
                logger.info(f"📝 Medium query ({word_count} words), Attempt {attempt}: Adding synonyms")
            else:
                rewritten = self._broaden_search(query)
                logger.info(f"📝 Medium query ({word_count} words), Attempt {attempt}: Broadening search")
        
        else:
            # Long queries: Extract key concepts
            if attempt == 0:
                rewritten = self._extract_key_concepts(query)
                logger.info(f"📝 Long query ({word_count} words), Attempt {attempt}: Extracting key concepts")
            elif attempt == 1:
                rewritten = self._extract_key_concepts(self._expand_keywords(query))
                logger.info(f"📝 Long query ({word_count} words), Attempt {attempt}: Key concepts + expansion")
            else:
                rewritten = self._broaden_search(query)
                logger.info(f"📝 Long query ({word_count} words), Attempt {attempt}: Core terms only")
        
        logger.info(f"   '{query}' → '{rewritten}'")
        return rewritten
    
    def _expand_keywords(self, query: str) -> str:
        """
        Attempt 0: Transform casual language to academic terms.
        
        Example: "why men suicide more" → "factors contributing to male suicide higher rates"
        """
        import re
        result = query.lower()
        
        # Apply transformations with word boundaries for safe replacement
        for pattern, replacement in self.TRANSFORMATIONS.items():
            if "\\b" in pattern:  # Use regex for word boundary patterns
                result = re.sub(pattern, replacement, result)
            elif pattern in result:  # Simple substring replacement for phrases
                result = result.replace(pattern, replacement)
                logger.debug(f"   Transformed '{pattern}' → '{replacement}'")
        
        return result.strip()
    
    def _add_synonyms(self, query: str) -> str:
        """
        Attempt 1: Add domain synonyms and related concepts.
        
        Example: "AI in healthcare" → "AI artificial intelligence machine learning in healthcare medical clinical"
        """
        query_lower = query.lower()
        result = query
        
        # Find and add synonyms
        for term, synonyms in self.SYNONYMS.items():
            if term.lower() in query_lower:
                # Add first 2-3 synonyms
                additions = synonyms[:3]
                result = f"{result} {' '.join(additions)}"
                logger.debug(f"   Added synonyms for '{term}': {additions}")
        
        return result.strip()
    
    def _broaden_search(self, query: str) -> str:
        """
        Attempt 2: Broaden to core concepts by removing specifics.
        
        Example: "quantum computing error correction algorithms" → "quantum computing algorithms"
        """
        words = query.lower().split()
        
        # Remove stopwords
        important_words = [w for w in words if w not in self.STOPWORDS and len(w) > 3]
        
        # Keep only the most important 3-5 words
        core_terms = important_words[:5]
        
        result = " ".join(core_terms)
        logger.debug(f"   Kept core terms: {core_terms}")
        
        return result.strip()
    
    def _extract_key_concepts(self, query: str) -> str:
        """
        🎯 Phase 4: Extract key concepts from long queries.
        
        For queries with 11+ words, this extracts the most important terms
        to avoid diluting the search with too much context.
        
        Example: 
        "explain the detailed mechanisms of how quantum entanglement enables 
         quantum computing to solve certain problems faster than classical computers"
        → "quantum entanglement quantum computing algorithms performance"
        
        Strategy:
        1. Remove stopwords
        2. Keep longer words (more specific terms)
        3. Identify potential academic phrases
        4. Select top 6-8 terms
        """
        words = query.lower().split()
        
        # Step 1: Remove stopwords
        filtered_words = [w for w in words if w not in self.STOPWORDS]
        
        # Step 2: Score words by importance
        # - Longer words are more specific (higher score)
        # - Words that appear in our transformations/synonyms dicts are domain terms (bonus score)
        scored_words = []
        for word in filtered_words:
            score = len(word)  # Base score = length
            
            # Bonus for domain terms
            if any(word in term.lower() for term in self.SYNONYMS.keys()):
                score += 10
            if any(word in term.lower() for term in self.TRANSFORMATIONS.keys()):
                score += 5
            
            scored_words.append((word, score))
        
        # Step 3: Sort by score and take top terms
        scored_words.sort(key=lambda x: x[1], reverse=True)
        key_terms = [word for word, _ in scored_words[:8]]
        
        # Step 4: Build result maintaining some original order
        result_terms = []
        for word in words:
            if word.lower() in key_terms and word.lower() not in result_terms:
                result_terms.append(word.lower())
                if len(result_terms) >= 8:
                    break
        
        result = " ".join(result_terms)
        logger.debug(f"   Extracted {len(result_terms)} key terms from {len(words)} words")
        
        return result.strip()
    
    
    def get_all_variations(self, query: str) -> List[str]:
        """
        Get all query variations for debugging/logging.
        
        Returns:
            List of [original, attempt0, attempt1, attempt2]
        """
        return [
            query,
            self._expand_keywords(query),
            self._add_synonyms(query),
            self._broaden_search(query)
        ]
