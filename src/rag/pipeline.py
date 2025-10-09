from typing import List, Dict, Optional
import logging
from .embeddings import EmbeddingModel
from .vectorstore import VectorStore
from ..utils import clean_text, chunk_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(
        self,
        embedding_model: Optional[EmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None
    ):
        self.embedding_model = embedding_model or EmbeddingModel()
        self.vector_store = vector_store or VectorStore()

    async def process_and_store(
        self,
        texts: List[str],
        metadata: Optional[List[Dict]] = None
    ) -> List[str]:
        """
        Process texts and store in vectorstore
        """
        try:
            # Clean and chunk texts
            processed_chunks = []
            chunk_metadata = []
            
            for idx, text in enumerate(texts):
                cleaned_text = clean_text(text)
                chunks = chunk_text(cleaned_text)
                logger.info(f"Created {len(chunks)} chunks from text {idx+1}")
                processed_chunks.extend(chunks)
                
                # Replicate metadata for each chunk
                if metadata and len(metadata) > idx:
                    chunk_metadata.extend([metadata[idx]] * len(chunks))
            
            logger.info(f"Generating embeddings for {len(processed_chunks)} chunks")
            embeddings = self.embedding_model.embed_text(processed_chunks)
            if len(embeddings) == 0:
                logger.error("Failed to generate embeddings")
                return []
            
            logger.info("Storing chunks and embeddings in vectorstore")
            ids = await self.vector_store.add_texts(
                texts=processed_chunks,
                embeddings=embeddings.tolist(),
                metadatas=chunk_metadata
            )
            
            logger.info(f"Successfully stored {len(ids)} chunks")
            return ids
        except Exception as e:
            logger.error(f"Error in process_and_store: {str(e)}")
            return []

    async def retrieve_relevant(
        self,
        query: str,
        k: int = 3,
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Retrieve relevant chunks for a query
        """
        try:
            logger.info(f"Generating embedding for query: {query}")
            query_embedding = self.embedding_model.embed_text(query)
            if len(query_embedding) == 0:
                logger.error("Failed to generate query embedding")
                return []
            
            logger.info("Searching for relevant chunks")
            results = await self.vector_store.similarity_search(
                query_embedding=query_embedding.tolist(),
                k=k,
                threshold=threshold
            )
            
            logger.info(f"Found {len(results)} relevant chunks")
            return results
        except Exception as e:
            logger.error(f"Error in retrieve_relevant: {str(e)}")
            return []