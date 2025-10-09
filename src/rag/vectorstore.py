import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import logging
import numpy as np
import os

logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, persist_dir: str = "D:/autonomous_research_assistant/data/vectorstore"):
        self.persist_dir = persist_dir
        logger.info(f"Initializing ChromaDB with persist_dir: {persist_dir}")
        logger.info(f"ChromaDB version: {chromadb.__version__}")
        # Ensure persist_dir exists and is writable
        os.makedirs(persist_dir, exist_ok=True)
        if not os.access(persist_dir, os.W_OK):
            logger.error(f"Persist directory {persist_dir} is not writable")
            raise PermissionError(f"Cannot write to {persist_dir}")
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        # Explicitly delete and recreate collection to ensure clean state
        try:
            self.client.delete_collection("research_assistant")
            logger.info("Deleted existing research_assistant collection")
        except:
            logger.info("No existing research_assistant collection to delete")
        self.collection = self.client.create_collection(
            name="research_assistant",
            metadata={"hnsw:space": "cosine", "description": "Research content embeddings"}
        )
        logger.info("ChromaDB collection created")

    async def add_texts(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        try:
            if not ids:
                ids = [str(i) for i in range(len(texts))]
            
            logger.info(f"Adding {len(texts)} documents to vectorstore")
            logger.info(f"First document preview: {texts[0][:100]}...")
            logger.info(f"First embedding norm: {np.linalg.norm(embeddings[0])}")
            
            # Validate metadata
            metadatas = metadatas if metadatas else [{}] * len(texts)
            if len(metadatas) != len(texts):
                logger.error(f"Metadata length {len(metadatas)} does not match texts length {len(texts)}")
                return []
            
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            # Verify collection state
            count = self.collection.count()
            logger.info(f"Collection now has {count} documents")
            # Log stored data for debugging
            stored_data = self.collection.get()
            logger.info(f"Stored documents after add: {stored_data['documents']}")
            logger.info(f"Stored IDs after add: {stored_data['ids']}")
            
            logger.info(f"Successfully added {len(texts)} documents")
            return ids
        except Exception as e:
            logger.error(f"Error adding texts to vectorstore: {str(e)}")
            return []

    async def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 3,
        threshold: float = 0.7
    ) -> List[Dict]:
        try:
            logger.info(f"Searching for {k} most similar documents")
            logger.info(f"Query embedding norm: {np.linalg.norm(query_embedding)}")
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k
            )
            
            logger.info(f"Raw query results: {results}")
            documents = results['documents'][0]
            distances = results['distances'][0]
            metadatas = results['metadatas'][0]
            ids = results['ids'][0]
            
            # Filter by similarity threshold and create result objects
            similar_docs = []
            for doc, distance, metadata, id in zip(documents, distances, metadatas, ids):
                similarity_score = 1 - distance  # Convert distance to similarity
                logger.info(f"Retrieved chunk {id}: {doc[:50]}... (score: {similarity_score:.2f})")
                if similarity_score >= threshold:
                    similar_docs.append({
                        'text': doc,
                        'score': similarity_score,
                        'metadata': metadata,
                        'id': id
                    })
            
            logger.info(f"Found {len(similar_docs)} documents above threshold {threshold}")
            return similar_docs
        except Exception as e:
            logger.error(f"Error during similarity search: {str(e)}")
            return []