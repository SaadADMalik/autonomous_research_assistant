import logging
from typing import List, Dict, Union
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import numpy as np
import uuid
from ..utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(
        self,
        persist_dir: str = "D:/autonomous_research_assistant/data/vectorstore",
        embedding_model_name: str = "all-mpnet-base-v2",
        collection_name: str = "research_assistant",
        reset_collection: bool = False,
        use_memory: bool = False,  # 🔥 NEW: Support in-memory mode
    ):
        logger.info(f"Initializing ChromaDB (memory={use_memory}, persist_dir: {persist_dir})")
        logger.info(f"ChromaDB version: {chromadb.__version__}")
        logger.info(f"Using embedding model: {embedding_model_name}")
        
        # 🔥 Use in-memory client for temporary storage (prevents cross-query pollution)
        if use_memory or persist_dir == ":memory:":
            self.client = chromadb.EphemeralClient(settings=Settings())
            logger.info("✅ Using in-memory ChromaDB (no disk persistence)")
        else:
            self.client = chromadb.PersistentClient(path=persist_dir, settings=Settings())
            logger.info(f"Using persistent ChromaDB at {persist_dir}")
        
        self.collection_name = collection_name
        
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model_name
        )
        
        if reset_collection:
            try:
                self.client.delete_collection(name=self.collection_name)
                logger.info(f"Deleted existing {self.collection_name} collection")
            except Exception:
                logger.info(f"No existing {self.collection_name} collection to delete")

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
        )
        logger.info("ChromaDB collection ready: %s", self.collection_name)

    def delete_collection(self):
        """Delete the research_assistant collection."""
        try:
            self.client.delete_collection(name=self.collection_name)
            logger.info(f"Deleted {self.collection_name} collection")
            # Recreate immediately to keep object valid
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Recreated {self.collection_name} collection")
        except Exception as e:
            logger.error(f"Error in delete_collection: {str(e)}")

    async def add_texts(self, texts: List[str], metadata: List[Dict] = None) -> List[str]:
        logger.info(f"Adding {len(texts)} documents to vectorstore")
        logger.info(f"First document preview: {texts[0][:50]}..." if texts else "No documents provided")
        
        # Ensure metadata matches texts length
        if metadata is None:
            metadata = [{}] * len(texts)
        
        try:
            ids = [str(uuid.uuid4()) for _ in texts]
            self.collection.add(
                documents=texts,
                metadatas=metadata,
                ids=ids
            )
            logger.info(f"Collection now has {self.collection.count()} documents")
            logger.info(f"Successfully added {len(texts)} documents")
            return ids
        except Exception as e:
            logger.error(f"Error adding documents to vectorstore: {str(e)}")
            return []

    async def similarity_search(self, query_embedding: np.ndarray, k: int = 4, threshold: float = 0.0) -> List[Dict]:
        logger.info(f"Searching for {k} most similar documents")
        logger.info(f"Query embedding shape: {query_embedding.shape}")
        logger.info(f"Query embedding norm: {np.linalg.norm(query_embedding)}")
        try:
            query_emb = query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding
            if isinstance(query_emb, list) and query_emb and isinstance(query_emb[0], list):
                query_emb = query_emb[0]
            results = self.collection.query(
                query_embeddings=[query_emb],
                n_results=k,
                include=["metadatas", "documents", "distances"]
            )
            logger.info(f"Raw query results: {results}")
            
            retrieved = []
            for i, (doc, meta, dist) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
                score = 1 - dist
                logger.info(f"Retrieved chunk {i}: {doc[:50]}... (score: {score:.2f})")
                if score >= threshold:
                    retrieved.append({"text": doc, "metadata": meta, "score": score})
            
            logger.info(f"Found {len(retrieved)} documents above threshold {threshold}")
            return retrieved
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            return []