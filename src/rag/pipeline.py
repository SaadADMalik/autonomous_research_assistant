import logging
from typing import List, Dict
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
        """
        Chunk text into smaller pieces while preserving content and structure.
        
        Args:
            text: Input text to chunk
            chunk_size: Maximum size of each chunk in characters
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        try:
            # Clean the text but preserve structure
            cleaned_text = clean_text(text)
            
            # Log what we're working with
            logger.info(f"Original text length: {len(text)}, Cleaned length: {len(cleaned_text)}")
            logger.info(f"Cleaned text preview: {cleaned_text[:100]}...")
            
            # Check if text is too short after cleaning
            if not cleaned_text or len(cleaned_text) < 10:
                logger.warning(f"Text too short after cleaning (length: {len(cleaned_text)})")
                logger.warning(f"Original text was: {text[:200]}...")
                return []
            
            # Split into sentences (more robust approach)
            # Split on sentence boundaries: . ! ? followed by space or end of string
            sentences = []
            current_sentence = ""
            
            for i, char in enumerate(cleaned_text):
                current_sentence += char
                
                # Check if we're at a sentence boundary
                if char in '.!?' and (i == len(cleaned_text) - 1 or cleaned_text[i + 1].isspace()):
                    sentence = current_sentence.strip()
                    if sentence:
                        sentences.append(sentence)
                    current_sentence = ""
            
            # Add any remaining text as final sentence
            if current_sentence.strip():
                sentences.append(current_sentence.strip())
            
            logger.info(f"Split into {len(sentences)} sentences")
            
            if not sentences:
                logger.warning("No sentences found after splitting")
                # Fallback: treat entire text as one chunk if it's not too long
                if len(cleaned_text) <= chunk_size:
                    return [cleaned_text]
                else:
                    # Force split into chunks
                    chunks = []
                    for i in range(0, len(cleaned_text), chunk_size - overlap):
                        chunk = cleaned_text[i:i + chunk_size]
                        if chunk:
                            chunks.append(chunk)
                    logger.info(f"Created {len(chunks)} chunks via forced splitting")
                    return chunks
            
            # Combine sentences into chunks
            chunks = []
            current_chunk = ""
            
            for sentence in sentences:
                # If adding this sentence would exceed chunk_size, save current chunk and start new one
                if len(current_chunk) + len(sentence) + 1 > chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    # Start new chunk with overlap (last part of previous chunk)
                    overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                    current_chunk = overlap_text + " " + sentence
                else:
                    # Add sentence to current chunk
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
            
            # Add final chunk if it exists
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            logger.info(f"Created {len(chunks)} chunks from text")
            
            # Log first chunk for verification
            if chunks:
                logger.info(f"First chunk preview: {chunks[0][:100]}...")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking text: {str(e)}", exc_info=True)
            return []

    async def process_and_store(self, documents: List[str], metadata: List[Dict] = None) -> List[str]:
        """
        Process documents and store them in the vector store.
        
        Args:
            documents: List of document texts
            metadata: List of metadata dicts (one per document)
            
        Returns:
            List of document IDs that were stored
        """
        logger.info(f"Processing and storing {len(documents)} documents")
        
        try:
            all_chunks = []
            all_metadata = []
            
            for i, doc in enumerate(documents):
                logger.info(f"Processing document {i+1}/{len(documents)}")
                logger.info(f"Original document length: {len(doc)}")
                
                # Chunk the document
                chunks = self.chunk_text(doc)
                
                if not chunks:
                    logger.warning(f"No chunks generated for document {i+1}")
                    continue
                
                logger.info(f"Generated {len(chunks)} chunks for document {i+1}")
                
                # Add chunks to collection
                all_chunks.extend(chunks)
                
                # Assign metadata to each chunk
                doc_metadata = metadata[i] if metadata and i < len(metadata) else {"source": "unknown"}
                all_metadata.extend([doc_metadata] * len(chunks))
            
            if not all_chunks:
                logger.warning("No chunks generated from any documents")
                return []
            
            logger.info(f"Total chunks to store: {len(all_chunks)}")
            
            # Store chunks in vector store
            ids = await self.vector_store.add_texts(all_chunks, metadata=all_metadata)
            
            logger.info(f"Successfully stored {len(ids)} chunks")
            return ids
            
        except Exception as e:
            logger.error(f"Error in process_and_store: {str(e)}", exc_info=True)
            return []

    async def retrieve_relevant(self, query: str, k: int = 4, threshold: float = 0.0) -> List[Dict]:
        """
        Retrieve relevant documents for a given query.
        
        Args:
            query: Search query
            k: Number of documents to retrieve
            threshold: Minimum similarity threshold (0-1)
            
        Returns:
            List of dicts with 'text', 'metadata', and 'score' keys
        """
        try:
            logger.info(f"Retrieving relevant documents for query: '{query}'")
            
            # Generate query embedding
            query_embedding = self.embedding_model.embed_text(query)
            
            logger.info(f"Query embedding shape: {query_embedding.shape}")
            logger.info(f"Query embedding norm: {np.linalg.norm(query_embedding)}")
            
            # Search for similar documents
            results = await self.vector_store.similarity_search(
                query_embedding, 
                k=k, 
                threshold=threshold
            )
            
            logger.info(f"Retrieved {len(results)} relevant documents")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in retrieve_relevant: {str(e)}", exc_info=True)
            return []