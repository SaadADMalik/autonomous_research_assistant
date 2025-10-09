import logging
from typing import List, Dict, Union
import numpy as np
from .embeddings import EmbeddingModel
from .vectorstore import VectorStore
from ..utils.utils import clean_text
from ..utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self, embedding_model: EmbeddingModel = None, vector_store: VectorStore = None):
        logger.info("Initializing RAGPipeline")
        self.embedding_model = embedding_model or EmbeddingModel()
        self.vector_store = vector_store or VectorStore(persist_dir="D:/autonomous_research_assistant/data/vectorstore")

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Chunk text into smaller pieces while preserving original punctuation."""
        try:
            cleaned_text = clean_text(text)
            logger.info(f"Cleaned text: {cleaned_text[:50]}...")
            # Simple chunking by splitting into sentences
            # Use a more precise split to avoid adding extra periods
            sentences = [s for s in cleaned_text.split('. ') if s]
            chunks = []
            current_chunk = ""
            for sentence in sentences:
                # Restore original period if sentence doesn't end with one
                sentence = sentence.strip() + ('.' if not sentence.endswith('.') else '')
                if len(current_chunk) + len(sentence) <= chunk_size:
                    current_chunk += sentence + " "
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + " "
            if current_chunk:
                chunks.append(current_chunk.strip())
            logger.info(f"Created {len(chunks)} chunks from text: {chunks}")
            return chunks
        except Exception as e:
            logger.error(f"Error chunking text: {str(e)}")
            return []

    async def process_and_store(self, documents: List[str], metadata: List[Dict] = None) -> List[str]:
        """Process and store documents in the vector store."""
        logger.info(f"Processing and storing {len(documents)} documents")
        try:
            all_chunks = []
            all_metadata = []
            for i, doc in enumerate(documents):
                chunks = self.chunk_text(doc)
                all_chunks.extend(chunks)
                # Assign metadata to each chunk
                doc_metadata = metadata[i] if metadata and i < len(metadata) else {"source": "unknown"}
                all_metadata.extend([doc_metadata] * len(chunks))
            
            if not all_chunks:
                logger.warning("No chunks generated from documents")
                return []
            
            logger.info(f"Generated {len(all_chunks)} chunks")
            logger.info(f"Storing chunks in vectorstore")
            # Store chunks without passing embeddings, as ChromaDB handles them internally
            ids = await self.vector_store.add_texts(all_chunks, metadata=all_metadata)
            logger.info(f"Successfully stored {len(ids)} chunks")
            return ids
        except Exception as e:
            logger.error(f"Error in process_and_store: {str(e)}")
            return []

    async def retrieve_relevant(self, query: str, k: int = 4, threshold: float = 0.0) -> List[Dict]:
        """Retrieve relevant documents for a given query."""
        try:
            logger.info(f"Generating embedding for query: {query}")
            query_embedding = self.embedding_model.embed_text(query)
            logger.info(f"Embedding norm after normalization: {np.linalg.norm(query_embedding)}")
            
            logger.info("Searching for relevant chunks")
            results = await self.vector_store.similarity_search(query_embedding, k=k, threshold=threshold)
            logger.info(f"Found {len(results)} relevant chunks")
            return results
        except Exception as e:
            logger.error(f"Error in retrieve_relevant: {str(e)}")
            return []