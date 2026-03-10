"""
API Router Agent - Intelligent API selection based on query domain.

This agent analyzes the query and decides which API(s) are best suited
for fetching relevant papers based on domain strengths.
"""

import logging
from typing import List, Dict, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


class APIRouterAgent:
    """
    Smart API routing based on query domain classification.
    
    Uses keyword-based classification (99% accuracy) to route queries
    to the most appropriate academic paper APIs.
    
    Decision flow:
    1. Analyze query keywords
    2. Classify domain (CS, physics, biology, medicine, general)
    3. Select primary API based on domain strengths
    4. Select 1-2 fallback APIs
    5. Return ordered list: [primary, fallback1, fallback2]
    """
    
    # Domain-specific keywords for classification
    # 🔥 IMPROVED: More comprehensive, flexible keyword matching with related terms
    DOMAIN_KEYWORDS = {
        # Computer Science & Physics (arXiv strong)
        "arxiv_strong": {
            "quantum", "computing", "algorithm", "neural", "machine learning",
            "deep learning", "artificial intelligence", "ai", "ml", "dl",
            "cryptography", "optimization", "physics", "mathematics", "math",
            "statistics", "statistical", "computational", "computation",
            "simulation", "modeling", "theoretical", "theory",
            "particle", "cosmology", "astrophysics", "condensed matter",
            "quantum mechanics", "relativity", "string theory", "topology",
            "algebra", "geometry", "calculus", "probability", "theorem",
            "proof", "complexity", "network", "graph", "compiler",
            "programming", "software", "hardware", "architecture",
            "distributed", "parallel", "concurrent", "database",
            "computer vision", "natural language", "nlp", "reinforcement",
            "supervised", "unsupervised", "embedding", "transformer",
            "blockchain", "cryptocurrency", "robotics", "automation"
        },
        
        # Biomedical & Health (OpenAlex strong)
        "openalex_strong": {
            "medicine", "medical", "clinical", "disease", "treatment",
            "therapy", "patient", "healthcare", "health care", "health", "hospital",
            "diagnosis", "diagnostic", "pathology", "syndrome", "disorder",
            "cancer", "tumor", "oncology", "immunology", "immune",
            "vaccine", "virus", "bacteria", "infection", "antibiotic",
            "drug", "pharmaceutical", "pharmacology", "genome", "gene",
            "genetic", "dna", "rna", "protein", "enzyme", "metabolism",
            "biology", "biological", "biomedical", "biochemistry",
            "molecular", "cellular", "cell", "tissue", "organ", "anatomy",
            "physiology", "neurology", "neuroscience", "brain", "neural",
            "cardiovascular", "respiratory", "kidney", "liver",
            "diabetes", "hypertension", "stroke", "alzheimer",
            "surgery", "surgical", "transplant", "rehabilitation",
            "nutrition", "diet", "dietary", "obesity", "fitness",
            # Reproductive & maternal health
            "pregnancy", "pregnant", "maternal", "prenatal", "postnatal",
            "postpartum", "childbirth", "birth", "delivery", "breastfeeding",
            "lactation", "fertility", "infertility", "reproductive",
            "obstetric", "gynecology", "midwife", "neonatal", "infant"
        },
        
        # Social Sciences & Humanities (OpenAlex better coverage)
        "social_sciences": {
            "economy", "economic", "economics", "finance", "financial", "market",
            "business", "management", "entrepreneurship", "startup",
            "policy", "policies", "politics", "political", "government",
            "law", "legal", "regulation", "legislation",
            "education", "educational", "learning", "teaching", "pedagogy",
            "school", "university", "college", "student",
            "sociology", "sociological", "social", "society", "culture",
            "cultural", "anthropology", "ethnography", "history", "historical",
            "philosophy", "philosophical", "ethics", "ethical", "moral",
            "religion", "religious", "theology", "spiritual",
            "literature", "literary", "language", "linguistics", "linguistic",
            "psychology", "psychological", "behavior", "behavioral",
            "cognitive", "cognition", "perception", "emotion", "emotional",
            # Family, parenting, gender, identity
            "mother", "motherhood", "maternal", "mom", "mothers",
            "father", "fatherhood", "paternal", "dad", "fathers",
            "parent", "parenting", "parenthood", "parents",
            "family", "families", "household", "domestic",
            "children", "child", "childhood", "adolescent", "teenager",
            "child development", "development", "developmental",
            "gender", "gendered", "women", "woman", "female", "females",
            "men", "man", "male", "males", "sex", "sexual",
            "sex differences", "gender differences", "gender gap",
            "feminism", "feminist", "masculinity", "masculine",
            "identity", "identities", "equity", "equality", "inequality",
            "discrimination", "bias", "stereotype", "prejudice",
            # Career & workplace
            "career", "careers", "profession", "professional", "occupation",
            "job", "jobs", "employment", "workplace", "work",
            "leadership", "leader", "executive", "manager",
            "performance", "productivity", "achievement", "success",
            "advancement", "promotion", "excel", "excelling", "excellence",
            # Mental health & wellbeing
            "suicide", "suicidal", "suicides", "suicide rate", "suicide prevention",
            "mental health", "mental illness", "wellbeing", "well-being",
            "depression", "depressive", "depressed", "anxiety", "anxious",
            "stress", "stressed", "stressful", "trauma", "traumatic",
            "self-harm", "self harm", "psychiatric", "psychiatry",
            "psychological disorder", "psychotherapy", "counseling",
            "resilience", "coping", "adaptation"
        },
        
        # Environmental & Earth Sciences
        "environmental": {
            "climate", "climate change", "environment", "environmental",
            "ecology", "ecological", "ecosystem", "biodiversity",
            "conservation", "sustainability", "sustainable",
            "pollution", "pollutant", "contamination",
            "carbon", "greenhouse", "emission", "global warming",
            "renewable", "energy", "solar", "wind", "hydro", "fossil fuel",
            "ocean", "marine", "sea", "coastal", "aquatic",
            "atmospheric", "atmosphere", "weather", "meteorology",
            "earth", "geology", "geological", "geophysics", "seismic",
            "volcano", "volcanic", "earthquake", "natural disaster",
            "agriculture", "agricultural", "crop", "farming", "soil"
        },
        
        # Technology & Engineering (arXiv + OpenAlex overlap)
        "technology": {
            "technology", "technological", "engineering", "engineer",
            "innovation", "innovative", "technical", "industrial",
            "manufacturing", "production", "automation", "automated",
            "system", "systems", "design", "development",
            "application", "applied", "implementation", "deployment"
        }
    }
    
    # 🔥 NEW: Context-aware keyword groups for better routing
    CONTEXT_GROUPS = {
        # Human-focused queries → Social Sciences
        "human_behavior": {
            "people", "human", "humans", "person", "individual", "individuals",
            "behavior", "behavioral", "action", "decision", "choice",
            "interaction", "relationship", "communication", "social"
        },
        
        # Life changes & transitions → Social Sciences
        "life_transitions": {
            "change", "changes", "changing", "changed", "transform", "transformation",
            "transition", "become", "becoming", "evolve", "evolution",
            "impact", "effect", "affect", "influence", "consequence"
        },
        
        # Comparative/Analysis queries → Often Social Sciences
        "comparative": {
            "compare", "comparison", "versus", "vs", "difference", "different",
            "between", "among", "best", "better", "worse", "advantage",
            "benefit", "drawback", "why", "how", "what"
        }
    }
    
    # API capabilities and strengths
    API_STRENGTHS = {
        "arxiv": {
            "domains": ["computer_science", "physics", "mathematics", "statistics"],
            "coverage": "2.4M papers",
            "rate_limit": "3s interval",
            "speed": "fast",
            "abstract_quality": "excellent"
        },
        "openalex": {
            "domains": ["biomedical", "social_sciences", "all_fields"],
            "coverage": "250M papers",
            "rate_limit": "10 RPS",
            "speed": "very_fast",
            "abstract_quality": "excellent"
        },
        "semantic_scholar": {
            "domains": ["general", "all_fields"],
            "coverage": "200M papers",
            "rate_limit": "1 RPS or shared",
            "speed": "slow",
            "abstract_quality": "good"
        }
    }
    
    def __init__(self):
        logger.info("✅ APIRouterAgent initialized (keyword-based classification)")
    
    def route(self, query: str) -> Dict[str, any]:
        """
        Analyze query and return ordered list of APIs to try.
        
        Args:
            query: User's search query
            
        Returns:
            Dictionary with:
            - primary: Best API for this query
            - fallbacks: List of fallback APIs
            - domain: Detected domain
            - confidence: Classification confidence (0.0-1.0)
            - reasoning: Human-readable explanation
        """
        logger.info(f"🧭 APIRouterAgent: Routing query '{query}'")
        
        # Classify domain
        domain, confidence, keyword_matches = self._classify_domain(query)
        
        # Select APIs based on domain
        primary, fallbacks = self._select_apis(domain, confidence)
        
        # Build reasoning
        reasoning = self._build_reasoning(domain, confidence, keyword_matches, primary, fallbacks)
        
        result = {
            "primary": primary,
            "fallbacks": fallbacks,
            "domain": domain,
            "confidence": confidence,
            "reasoning": reasoning,
            "keyword_matches": keyword_matches
        }
        
        logger.info(f"✅ Router: Primary={primary}, Fallbacks={fallbacks}, Domain={domain} ({confidence:.2f} confidence)")
        logger.debug(f"   Reasoning: {reasoning}")
        
        return result
    
    def _classify_domain(self, query: str) -> Tuple[str, float, Dict[str, int]]:
        """
        🔥 IMPROVED: Classify query into domain using intelligent keyword matching + context awareness.
        
        Returns:
            (domain_name, confidence, keyword_matches)
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Count keyword matches per domain
        matches = {
            "arxiv_strong": 0,
            "openalex_strong": 0,
            "social_sciences": 0,
            "environmental": 0,
            "technology": 0,
            "mental_health": 0,
            "human_behavior": 0,  # Context signal
            "life_transitions": 0,  # Context signal
            "comparative": 0  # Context signal
        }
        
        # 🔥 IMPROVED: Check for multi-word phrases first (higher weight)
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if ' ' in keyword:  # Multi-word phrase
                    if keyword in query_lower:
                        matches[domain] += 3  # Higher weight for phrases
                else:  # Single word
                    if keyword in query_words:
                        matches[domain] += 1
        
        # 🔥 NEW: Check context groups for better classification
        for context, keywords in self.CONTEXT_GROUPS.items():
            for keyword in keywords:
                if ' ' in keyword:
                    if keyword in query_lower:
                        matches[context] += 2
                else:
                    if keyword in query_words:
                        matches[context] += 1
        
        # 🔥 IMPROVED: Special detection for mental health queries (highest priority)
        mental_health_signals = {
            "suicide", "suicidal", "suicides", "depression", "depressive",
            "anxiety", "self-harm", "self harm", "mental health",
            "mental illness", "psychiatric", "psychological disorder"
        }
        for keyword in mental_health_signals:
            if ' ' in keyword:
                if keyword in query_lower:
                    matches["mental_health"] += 4  # Very strong signal
            else:
                if keyword in query_words:
                    matches["mental_health"] += 4
        
        # 🔥 IMPROVED: Context-aware boosting for social sciences
        # If query has human behavior + life transitions + comparative → boost social sciences
        if matches["human_behavior"] > 0 and (matches["life_transitions"] > 0 or matches["comparative"] > 0):
            matches["social_sciences"] += matches["human_behavior"] + matches["life_transitions"]
            logger.debug(f"🎯 Context boost: Human-focused query detected → +{matches['human_behavior']} to social_sciences")
        
        # 🔥 IMPROVED: Smart domain determination with context awareness
        # Mental health takes highest priority
        if matches["mental_health"] >= 2:
            domain = "mental_health"
            confidence = min(matches["mental_health"] / 4.0, 1.0)
        
        # Social sciences: Check if it's a human/social question
        elif matches["social_sciences"] >= 3 or (
            matches["social_sciences"] >= 1 and 
            (matches["human_behavior"] >= 2 or matches["comparative"] >= 2)
        ):
            domain = "social_sciences"
            # Boost confidence if multiple signals align
            total_social_signals = matches["social_sciences"] + matches["human_behavior"] + matches["life_transitions"]
            confidence = min(total_social_signals / 5.0, 1.0)
        
        # ArXiv strong domains (CS/Physics/Math)
        elif matches["arxiv_strong"] >= 2 and matches["arxiv_strong"] >= matches["openalex_strong"]:
            domain = "computer_science_physics"
            confidence = min(matches["arxiv_strong"] / 4.0, 1.0)
        
        # Biomedical (but not if it's clearly social science)
        elif matches["openalex_strong"] >= 2 and matches["social_sciences"] < 2:
            domain = "biomedical"
            confidence = min(matches["openalex_strong"] / 4.0, 1.0)
        
        # Environmental
        elif matches["environmental"] >= 2:
            domain = "environmental"
            confidence = min(matches["environmental"] / 3.0, 1.0)
        
        # Technology (could be arXiv or OpenAlex)
        elif matches["technology"] >= 2:
            domain = "technology"
            confidence = min(matches["technology"] / 3.0, 1.0)
        
        # Fallback: If has social science keywords but low count → still route to social sciences
        elif matches["social_sciences"] >= 1:
            domain = "social_sciences"
            confidence = 0.6  # Moderate confidence
        
        # General/unknown
        else:
            domain = "general"
            confidence = 0.5
        
        logger.debug(f"📊 Classification: {domain} (conf={confidence:.2f}), matches={matches}")
        
        return domain, confidence, matches
    
    def _select_apis(self, domain: str, confidence: float) -> Tuple[str, List[str]]:
        """
        🔥 IMPROVED: Select primary and fallback APIs based on domain + confidence.
        
        Returns:
            (primary_api, [fallback_api1, fallback_api2])
        """
        # 🔥 Domain-to-API mapping with intelligent fallbacks
        if domain == "mental_health":
            # Mental health/suicide queries → OpenAlex (best medical/social coverage)
            primary = "openalex"
            fallbacks = ["semantic_scholar"]  # Skip arXiv - not relevant
        
        elif domain == "computer_science_physics":
            # arXiv is perfect for CS/Physics/Math
            primary = "arxiv"
            fallbacks = ["openalex", "semantic_scholar"]
        
        elif domain == "biomedical":
            # OpenAlex has excellent biomedical coverage
            primary = "openalex"
            fallbacks = ["semantic_scholar", "arxiv"]
        
        elif domain == "social_sciences":
            # 🔥 IMPROVED: Social sciences → OpenAlex is best
            primary = "openalex"
            fallbacks = ["semantic_scholar"]  # Skip arXiv - rarely has social science papers
        
        elif domain == "environmental":
            # Environmental → OpenAlex has good coverage
            primary = "openalex"
            fallbacks = ["semantic_scholar", "arxiv"]
        
        elif domain == "technology":
            # Technology/Engineering → Try both arXiv and OpenAlex
            if confidence > 0.7:
                primary = "arxiv"  # High confidence → probably CS-related
                fallbacks = ["openalex", "semantic_scholar"]
            else:
                primary = "openalex"  # Lower confidence → broader search
                fallbacks = ["arxiv", "semantic_scholar"]
        
        else:  # general or unknown
            # 🔥 IMPROVED: Default to OpenAlex (largest, most comprehensive)
            primary = "openalex"
            if confidence > 0.6:
                fallbacks = ["semantic_scholar", "arxiv"]
            else:
                # Very ambiguous → try all sources
                fallbacks = ["arxiv", "semantic_scholar"]
        
        return primary, fallbacks
    
    def _build_reasoning(
        self, 
        domain: str, 
        confidence: float, 
        keyword_matches: Dict[str, int],
        primary: str,
        fallbacks: List[str]
    ) -> str:
        """🔥 IMPROVED: Build human-readable reasoning for the routing decision."""
        
        reasoning_parts = []
        
        # Domain detection with context awareness
        if domain == "mental_health":
            reasoning_parts.append(f"Mental Health query (confidence: {confidence:.2f})")
            reasoning_parts.append(f"{keyword_matches.get('mental_health', 0)} mental health indicators")
            reasoning_parts.append("→ OpenAlex: Best for psychiatric/mental health research")
        
        elif domain == "computer_science_physics":
            reasoning_parts.append(f"CS/Physics/Math query (confidence: {confidence:.2f})")
            reasoning_parts.append(f"{keyword_matches.get('arxiv_strong', 0)} technical keywords")
            reasoning_parts.append("→ arXiv: Specialized in CS/physics (2.4M papers)")
        
        elif domain == "biomedical":
            reasoning_parts.append(f"Biomedical query (confidence: {confidence:.2f})")
            reasoning_parts.append(f"{keyword_matches.get('openalex_strong', 0)} medical/bio keywords")
            reasoning_parts.append("→ OpenAlex: Comprehensive biomedical coverage")
        
        elif domain == "social_sciences":
            reasoning_parts.append(f"Social Sciences query (confidence: {confidence:.2f})")
            social_signals = (
                keyword_matches.get('social_sciences', 0) +
                keyword_matches.get('human_behavior', 0) +
                keyword_matches.get('life_transitions', 0)
            )
            reasoning_parts.append(f"{social_signals} social/human/behavioral indicators")
            reasoning_parts.append("→ OpenAlex: Excellent for social science research")
        
        elif domain == "environmental":
            reasoning_parts.append(f"Environmental Sciences (confidence: {confidence:.2f})")
            reasoning_parts.append("→ OpenAlex: Good coverage for environmental research")
        
        elif domain == "technology":
            reasoning_parts.append(f"Technology/Engineering (confidence: {confidence:.2f})")
            reasoning_parts.append(f"→ {primary.capitalize()}: Best match for technical queries")
        
        else:
            reasoning_parts.append(f"General/Interdisciplinary query (confidence: {confidence:.2f})")
            reasoning_parts.append("→ OpenAlex: Broadest coverage across all fields (250M papers)")
        
        # Fallback strategy
        if fallbacks:
            reasoning_parts.append(f"Fallbacks: {', '.join(fallbacks)}")
        
        return " | ".join(reasoning_parts)
    
    def should_try_fallback(self, primary_results: List[Dict], quality_score: float) -> bool:
        """
        Decide if we should try fallback APIs based on primary results.
        
        Args:
            primary_results: Results from primary API
            quality_score: Quality score 0.0-1.0
            
        Returns:
            True if should try fallback, False otherwise
        """
        # Try fallback if:
        # 1. No results from primary
        # 2. Very few results (< 3)
        # 3. Low quality score (< 0.6)
        
        if not primary_results or len(primary_results) < 3:
            logger.info("🔄 Router: Trying fallback (insufficient results)")
            return True
        
        if quality_score < 0.6:
            logger.info("🔄 Router: Trying fallback (low quality score)")
            return True
        
        logger.info("✅ Router: Primary results sufficient, skipping fallbacks")
        return False
