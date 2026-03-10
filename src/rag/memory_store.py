from datetime import datetime
from typing import Dict, List

from .vectorstore import VectorStore
from .embeddings import EmbeddingModel


class AgentMemoryStore:
    """In-memory episodic memory for current query summaries (no disk persistence to prevent pollution)."""

    def __init__(self, persist_dir: str = ":memory:"):
        self.embedding_model = EmbeddingModel(model_name="all-MiniLM-L6-v2")
        # 🔥 CRITICAL FIX: ALWAYS use in-memory store to prevent cross-query pollution
        self.store = VectorStore(
            use_memory=True,  # Force in-memory mode
            embedding_model_name="all-MiniLM-L6-v2",
            collection_name="agent_memory_temp",
            reset_collection=True,  # Always reset at initialization
        )

    async def remember(self, query: str, summary: str, metadata: Dict[str, object]) -> List[str]:
        # 🔥 FIX: Store summary WITHOUT "Query:" and "Summary:" prefixes to prevent nested pollution
        # The metadata already contains the query, so we don't need to duplicate it in the text
        memory_text = summary.strip()
        memory_metadata = {
            **(metadata or {}),
            "query": query,  # Store query in metadata instead of text
            "memory_type": "research_summary",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return await self.store.add_texts([memory_text], [memory_metadata])

    async def recall(self, query: str, k: int = 3) -> List[Dict[str, object]]:
        query_embedding = self.embedding_model.embed_text(query)
        if query_embedding.size == 0:
            return []
        return await self.store.similarity_search(query_embedding, k=k, threshold=0.15)
