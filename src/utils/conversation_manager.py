"""
🎯 Phase 2: Conversation Memory Manager

Handles:
- Session-based conversation history (last 10 exchanges)
- Paper caching per session (reuse for follow-ups)
- Context-aware responses using history
- LLM-based intent analysis and smart cache filtering

FREE Implementation: In-memory dict (no database needed)
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Single conversation turn"""
    query: str
    response: str
    timestamp: float
    papers_used: List[Dict] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class Session:
    """Conversation session with history and cached papers"""
    session_id: str
    created_at: float
    last_active: float
    turns: List[ConversationTurn] = field(default_factory=list)
    cached_papers: List[Dict] = field(default_factory=list)
    query_history: List[str] = field(default_factory=list)
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session expired (inactive for 30 min)"""
        return (time.time() - self.last_active) > (timeout_minutes * 60)
    
    def get_recent_context(self, max_turns: int = 5) -> List[ConversationTurn]:
        """Get last N conversation turns for context"""
        return self.turns[-max_turns:] if self.turns else []
    
    def add_turn(self, query: str, response: str, papers: List[Dict], confidence: float):
        """Add new conversation turn"""
        turn = ConversationTurn(
            query=query,
            response=response,
            timestamp=time.time(),
            papers_used=papers,
            confidence=confidence
        )
        self.turns.append(turn)
        self.query_history.append(query)
        self.last_active = time.time()
        
        # Limit history to last 10 turns
        if len(self.turns) > 10:
            self.turns = self.turns[-10:]
        if len(self.query_history) > 10:
            self.query_history = self.query_history[-10:]
    
    def cache_papers(self, papers: List[Dict]):
        """Cache papers for this session"""
        # Add new papers to cache
        for paper in papers:
            # Check if already cached (by title or DOI)
            paper_id = paper.get('doi') or paper.get('title', '')
            if not any(p.get('doi') == paper_id or p.get('title') == paper_id for p in self.cached_papers):
                self.cached_papers.append(paper)
        
        # Limit cache to 50 papers per session
        if len(self.cached_papers) > 50:
            self.cached_papers = self.cached_papers[-50:]
        
        logger.info(f"📦 Session {self.session_id[:8]}: Cached {len(papers)} new papers (total: {len(self.cached_papers)})")


class ConversationManager:
    """
    🎯 Phase 2: Manages conversation sessions with memory and paper caching.
    
    Features:
    - In-memory session storage (FREE, no database)
    - Auto-cleanup of expired sessions (30 min timeout)
    - Context-aware responses using conversation history
    - Paper caching for fast follow-ups
    
    Benefits:
    - Follow-up queries: 2-3s (vs 5-7s from scratch)
    - "Tell me more" works naturally
    - Context from previous questions
    - Still FREE (in-memory only)
    """
    
    def __init__(self, session_timeout_minutes: int = 30, use_llm_intent: bool = True):
        self.sessions: Dict[str, Session] = {}
        self.session_timeout = session_timeout_minutes
        self.total_sessions = 0
        self.use_llm_intent = use_llm_intent
        
        # Initialize LLM-based intent analyzer
        self.intent_analyzer = None
        if use_llm_intent:
            try:
                from src.utils.query_intent_analyzer import QueryIntentAnalyzer
                self.intent_analyzer = QueryIntentAnalyzer()
                logger.info(f"✅ ConversationManager initialized (timeout: {session_timeout_minutes}m, LLM intent: ON)")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize QueryIntentAnalyzer: {e}, falling back to rule-based")
                self.use_llm_intent = False
                logger.info(f"✅ ConversationManager initialized (timeout: {session_timeout_minutes}m, LLM intent: OFF)")
        else:
            logger.info(f"✅ ConversationManager initialized (timeout: {session_timeout_minutes}m, LLM intent: OFF)")
    
    def get_or_create_session(self, session_id: str) -> Session:
        """Get existing session or create new one"""
        # Cleanup expired sessions first
        self._cleanup_expired_sessions()
        
        if session_id not in self.sessions:
            self.sessions[session_id] = Session(
                session_id=session_id,
                created_at=time.time(),
                last_active=time.time()
            )
            self.total_sessions += 1
            logger.info(f"🆕 New session created: {session_id[:8]}... (total active: {len(self.sessions)})")
        else:
            # Update last active time
            self.sessions[session_id].last_active = time.time()
        
        return self.sessions[session_id]
    
    def add_turn(
        self, 
        session_id: str, 
        query: str, 
        response: str, 
        papers: List[Dict], 
        confidence: float
    ):
        """Add conversation turn to session"""
        session = self.get_or_create_session(session_id)
        session.add_turn(query, response, papers, confidence)
        session.cache_papers(papers)
        
        logger.info(f"💬 Session {session_id[:8]}: Turn #{len(session.turns)} added")
    
    def get_context(self, session_id: str, max_turns: int = 5) -> Optional[List[ConversationTurn]]:
        """Get recent conversation context"""
        if session_id in self.sessions:
            return self.sessions[session_id].get_recent_context(max_turns)
        return None
    
    def get_cached_papers(self, session_id: str) -> List[Dict]:
        """Get cached papers for follow-up queries"""
        if session_id in self.sessions:
            papers = self.sessions[session_id].cached_papers
            logger.info(f"📦 Session {session_id[:8]}: Retrieved {len(papers)} cached papers")
            return papers
        return []
    
    def is_follow_up(self, session_id: str, query: str) -> bool:
        """
        🎯 ENHANCED: Detect if query is a follow-up to previous conversation.
        
        Follow-up indicators:
        ✅ Starts with: "tell me more", "explain", "what about", etc.
        ✅ Short query (<10 words) - likely contextual
        ✅ Contains pronouns: "it", "that", "this", "they"
        ✅ Similar keywords to previous query (30%+ overlap)
        
        NEW: Topic shift detection:
        ❌ Dismissal phrases: "leave this", "forget that", "new topic"
        ❌ Domain switch: climate → AI, biology → finance (prevents hallucinations)
        ❌ No keyword overlap with recent context
        """
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        if not session.query_history:
            return False
        
        query_lower = query.lower().strip()
        
        # 🚫 CRITICAL: Check for dismissal phrases (user wants to change topic)
        dismissal_phrases = [
            "leave this", "forget that", "forget about", "never mind",
            "new question", "different question", "different topic", "new topic",
            "changing subject", "change subject", "moving on", "move on",
            "switch to", "instead", "rather than", "something else",
            "let's talk about", "talk about something"
        ]
        
        if any(phrase in query_lower for phrase in dismissal_phrases):
            logger.info(f"🚫 NOT follow-up: '{query}' (dismissal phrase detected)")
            return False
        
        # 🎯 CRITICAL: Check for topic domain shifts (prevents hallucinations)
        current_topics = self._extract_topic_keywords(query_lower)
        previous_topics = self._extract_topic_keywords(" ".join(session.query_history[-3:]))
        
        # If completely different domains, it's NOT a follow-up
        if self._is_different_domain(current_topics, previous_topics):
            logger.info(f"🚫 NOT follow-up: '{query}' (topic domain shifted: {previous_topics} → {current_topics})")
            return False
        
        # Follow-up phrases (but only if topic hasn't shifted)
        follow_up_phrases = [
            "tell me more", "tell me about", "explain", "what about", "how about",
            "can you elaborate", "more details", "expand on",
            "what else", "also", "additionally", "furthermore",
            "which", "what", "why", "how", "when", "where"
        ]
        
        if any(phrase in query_lower for phrase in follow_up_phrases):
            logger.info(f"🔄 Follow-up detected: '{query}' (follow-up phrase found)")
            return True
        
        # Very short queries (<6 words) after an existing conversation are likely follow-ups
        # Examples: "good or bad?", "which one?", "how so?", "statistics?", "examples?"
        words = query.split()
        if len(words) <= 5 and len(session.query_history) > 0:
            logger.info(f"🔄 Follow-up detected: '{query}' (short contextual question)")
            return True
        
        # Short queries with pronouns
        if len(words) < 10:
            pronouns = ["it", "that", "this", "they", "them", "those", "these"]
            query_words = [w.strip("?.,!") for w in query_lower.split()]
            if any(pronoun in query_words for pronoun in pronouns):
                logger.info(f"🔄 Follow-up detected: '{query}' (pronoun + short query)")
                return True
        
        # 🎯 ENHANCED: Similar keywords to last query (require 30%+ meaningful overlap)
        last_query = session.query_history[-1].lower()
        
        # Remove stop words for better matching
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'should', 'could', 'may', 'might', 'must',
            'can', 'of', 'to', 'in', 'for', 'on', 'with', 'by', 'at', 'from'
        }
        
        query_keywords = set(w for w in query_lower.split() if w not in stop_words and len(w) > 2)
        last_keywords = set(w for w in last_query.split() if w not in stop_words and len(w) > 2)
        
        if query_keywords and last_keywords:
            overlap = query_keywords & last_keywords
            overlap_ratio = len(overlap) / min(len(query_keywords), len(last_keywords))
            
            # Require 30%+ meaningful overlap (prevents weak matches)
            if overlap_ratio >= 0.3:
                logger.info(f"🔄 Follow-up detected: '{query}' (keyword overlap {overlap_ratio:.0%} with previous)")
                return True
        
        logger.info(f"🆕 NEW topic: '{query}' (no follow-up indicators)")
        return False
    
    def _extract_topic_keywords(self, text: str) -> set:
        """
        Extract domain-specific topic keywords for shift detection.
        
        Major domains:
        - Climate/Environment: climate, biodiversity, species, temperature, ecosystem
        - AI/ML: ai, artificial intelligence, machine learning, deep learning, neural
        - Biotech/Medicine: biotech, medicine, drug, gene, protein, dna
        - Finance/Economics: finance, economy, stock, investment, market
        - Physics/Astronomy: physics, quantum, astronomy, universe, particle
        """
        # Define domain keywords
        climate_keywords = {
            'climate', 'biodiversity', 'species', 'temperature', 'ecosystem',
            'warming', 'carbon', 'emissions', 'pollution', 'habitat', 'extinction',
            'environmental', 'weather', 'ocean', 'ice', 'coral', 'forest'
        }
        
        ai_keywords = {
            'ai', 'artificial', 'intelligence', 'machine', 'learning', 'deep',
            'neural', 'network', 'algorithm', 'model', 'training', 'data',
            'robot', 'automation', 'computer', 'vision', 'nlp', 'gpt', 'llm'
        }
        
        biotech_keywords = {
            'biotech', 'biotechnology', 'medicine', 'medical', 'drug', 'gene',
            'protein', 'dna', 'rna', 'therapy', 'disease', 'vaccine', 'clinical',
            'pharmaceutical', 'biology', 'cell', 'molecular', 'genomics'
        }
        
        finance_keywords = {
            'finance', 'financial', 'economy', 'economic', 'stock', 'investment',
            'market', 'trading', 'bank', 'money', 'currency', 'crypto', 'bitcoin'
        }
        
        physics_keywords = {
            'physics', 'quantum', 'astronomy', 'universe', 'particle', 'atom',
            'energy', 'force', 'gravity', 'relativity', 'mechanics', 'photon'
        }
        
        text_lower = text.lower()
        found_topics = set()
        
        if any(kw in text_lower for kw in climate_keywords):
            found_topics.add('climate')
        if any(kw in text_lower for kw in ai_keywords):
            found_topics.add('ai')
        if any(kw in text_lower for kw in biotech_keywords):
            found_topics.add('biotech')
        if any(kw in text_lower for kw in finance_keywords):
            found_topics.add('finance')
        if any(kw in text_lower for kw in physics_keywords):
            found_topics.add('physics')
        
        return found_topics
    
    def _is_different_domain(self, current_topics: set, previous_topics: set) -> bool:
        """
        Check if current query is in a completely different domain.
        
        Returns True if:
        - Current has topics AND previous has topics
        - No overlap between current and previous topics
        
        Example:
        - Previous: {'climate'}, Current: {'ai', 'biotech'} → True (different domain)
        - Previous: {'climate'}, Current: {'climate', 'ai'} → False (overlapping domain)
        - Previous: {'climate'}, Current: set() → False (no clear domain)
        """
        # If either has no clear topics, can't determine domain shift
        if not current_topics or not previous_topics:
            return False
        
        # If they share at least one topic, it's in the same domain
        if current_topics & previous_topics:
            return False
        
        # Completely different domains
        return True
    
    def format_context_for_llm(self, session_id: str, max_turns: int = 3) -> str:
        """
        Format conversation context for LLM prompt.
        
        Args:
            session_id: Session ID
            max_turns: Number of recent turns to include
            
        Returns:
            Formatted context string for LLM prompt
        """
        context = self.get_context(session_id, max_turns)
        if not context:
            return ""
        
        formatted = "\n\nPrevious conversation:\n"
        for i, turn in enumerate(context, 1):
            formatted += f"\nUser: {turn.query}\n"
            # Truncate long responses
            response_preview = turn.response[:200] + "..." if len(turn.response) > 200 else turn.response
            formatted += f"Assistant: {response_preview}\n"
        
        formatted += "\nCurrent question (use context above if relevant):\n"
        
        return formatted
    
    def analyze_query_and_filter_cache(
        self, 
        session_id: str, 
        query: str
    ) -> Tuple[bool, List[Dict], Optional[Dict]]:
        """
        🎯 PRODUCTION: LLM-based query analysis with smart cache filtering.
        
        Fixes hallucination issues by:
        1. Understanding true query intent (e.g., "other animals" in cloning context = "cloning animals")
        2. Filtering cached papers by semantic relevance (only use if >60% relevant)
        3. Returning enhanced search query for better results
        
        Returns:
            (is_follow_up, relevant_cached_papers, query_intent)
        """
        # If LLM intent is disabled, fall back to rule-based
        if not self.use_llm_intent or not self.intent_analyzer:
            is_follow_up = self.is_follow_up(session_id, query)
            cached_papers = self.get_cached_papers(session_id) if is_follow_up else []
            return (is_follow_up, cached_papers, None)
        
        try:
            # Get conversation history
            session = self.get_or_create_session(session_id)
            conversation_history = session.query_history
            
            # Analyze query intent with LLM
            logger.info(f"🔍 Analyzing intent for: '{query[:60]}...'")
            query_intent = self.intent_analyzer.analyze_query_intent(
                current_query=query,
                conversation_history=conversation_history
            )
            
            is_follow_up = query_intent.get("is_follow_up", False)
            
            # If not a follow-up, no cache to filter
            if not is_follow_up:
                logger.info(f"🆕 NEW topic detected: {query_intent.get('main_topic', 'unknown')}")
                return (False, [], query_intent)
            
            # Check cache relevance for follow-up queries
            cached_papers = session.cached_papers
            if not cached_papers:
                logger.info("📦 No cached papers available")
                return (True, [], query_intent)
            
            # Get paper titles for relevance check
            paper_titles = [p.get('title', 'Untitled') for p in cached_papers]
            
            # Check if cached papers are relevant to current query
            relevance_score = self.intent_analyzer.check_cache_relevance(
                query=query,
                query_intent=query_intent,
                cached_paper_titles=paper_titles
            )
            
            # Use cache only if relevance is high (>0.6)
            if relevance_score >= 0.6:
                logger.info(f"✅ Using {len(cached_papers)} cached papers (relevance: {relevance_score:.2f})")
                return (True, cached_papers, query_intent)
            else:
                logger.info(f"🚫 Cache not relevant (score: {relevance_score:.2f}), will fetch new papers")
                # Still a follow-up, but need new papers
                return (True, [], query_intent)
                
        except Exception as e:
            logger.error(f"⚠️ Intent analysis failed: {e}, falling back to rule-based")
            # Fallback to rule-based detection
            is_follow_up = self.is_follow_up(session_id, query)
            cached_papers = self.get_cached_papers(session_id) if is_follow_up else []
            return (is_follow_up, cached_papers, None)
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions to free memory"""
        expired = [
            sid for sid, session in self.sessions.items()
            if session.is_expired(self.session_timeout)
        ]
        
        for sid in expired:
            turns = len(self.sessions[sid].turns)
            del self.sessions[sid]
            logger.info(f"🧹 Cleaned up expired session {sid[:8]}... ({turns} turns)")
        
        if expired:
            logger.info(f"🧹 Cleanup: Removed {len(expired)} sessions, {len(self.sessions)} active")
    
    def get_stats(self) -> Dict:
        """Get conversation manager statistics"""
        return {
            "active_sessions": len(self.sessions),
            "total_sessions_created": self.total_sessions,
            "total_turns": sum(len(s.turns) for s in self.sessions.values()),
            "total_cached_papers": sum(len(s.cached_papers) for s in self.sessions.values())
        }
