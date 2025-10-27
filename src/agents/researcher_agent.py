import logging
from typing import List
from src.rag.pipeline import RAGPipeline
from .base import AgentInput, AgentOutput
from src.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class ResearcherAgent:
    def __init__(self):
        logger.info(" Initializing ResearcherAgent")
        try:
            self.rag_pipeline = RAGPipeline()
            logger.info(" RAG Pipeline initialized successfully")
        except Exception as e:
            logger.error(f" Failed to initialize RAG Pipeline: {str(e)}")
            self.rag_pipeline = None

    def _extract_document_content(self, doc) -> str:
        """
        Extract full content from document in priority order.
        Ensures we get maximum available content.
        """
        if isinstance(doc, dict):
            # Priority order for content extraction
            content_sources = [
                doc.get("summary"),
                doc.get("abstract"),
                doc.get("content"),
                doc.get("text"),
                doc.get("body")
            ]
            
            # Get the first non-empty content
            for content in content_sources:
                if content and isinstance(content, str) and content.strip():
                    return content.strip()
            
            # Fallback: combine title + available content
            title = doc.get("title", "")
            summary = doc.get("summary", "")
            abstract = doc.get("abstract", "")
            
            combined = f"{title} {summary} {abstract}".strip()
            if combined:
                return combined
        
        elif isinstance(doc, str):
            return doc.strip()
        
        logger.warning(f" Could not extract content from document: {type(doc)}")
        return ""

    async def run(self, input_data: AgentInput, documents: List = None) -> AgentOutput:
        logger.info(f" Running ResearcherAgent with query: {input_data.query}")
        
        try:
            # Validate inputs
            if not input_data.query or not input_data.query.strip():
                logger.error(" Empty query provided")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={
                        "source": "researcher",
                        "error": "Empty query"
                    }
                )
            
            if not documents:
                logger.warning(" No documents provided to researcher")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={
                        "source": "researcher",
                        "error": "No documents provided"
                    }
                )
            
            # Extract full content from all documents
            doc_texts = []
            doc_metadata = []
            
            for i, doc in enumerate(documents):
                try:
                    content = self._extract_document_content(doc)
                    
                    if content:
                        doc_texts.append(content)
                        
                        # Extract metadata
                        meta = {
                            "source": "researcher",
                            "doc_index": i,
                            "title": doc.get("title", "") if isinstance(doc, dict) else "Document",
                            "query": input_data.query
                        }
                        doc_metadata.append(meta)
                        
                        logger.debug(f" Document {i+1}: {content[:60]}...")
                    else:
                        logger.warning(f" Document {i+1}: No content extracted")
                        
                except Exception as e:
                    logger.warning(f" Error extracting content from document {i+1}: {str(e)}")
                    continue
            
            if not doc_texts:
                logger.error(" No valid documents after content extraction")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={
                        "source": "researcher",
                        "error": "No valid document content"
                    }
                )
            
            logger.info(f" Extracted content from {len(doc_texts)} documents")
            
            # Store documents in RAG pipeline if available
            if self.rag_pipeline:
                try:
                    logger.debug(f" Storing {len(doc_texts)} documents in RAG pipeline")
                    ids = await self.rag_pipeline.process_and_store(
                        doc_texts, 
                        metadata=doc_metadata
                    )
                    
                    if ids:
                        logger.info(f" Stored {len(ids)} document chunks")
                    else:
                        logger.warning(" Failed to store documents, continuing with retrieval")
                        
                except Exception as e:
                    logger.warning(f" RAG storage failed: {str(e)}, continuing...")
            
            # Retrieve relevant documents
            try:
                logger.debug(f" Retrieving relevant content for query: {input_data.query}")
                results = await self.rag_pipeline.retrieve_relevant(
                    query=input_data.query,
                    k=3,
                    threshold=0.1
                )
                
                if not results:
                    logger.warning(" No relevant documents retrieved from RAG")
                    # Fallback: use all document texts directly
                    combined_text = "\n\n".join(doc_texts[:3])
                    logger.info(f" Using first {len(doc_texts[:3])} documents as fallback")
                    
                    return AgentOutput(
                        result=combined_text,
                        confidence=0.7,
                        metadata={
                            "source": "researcher",
                            "method": "direct_fallback",
                            "document_count": len(doc_texts)
                        }
                    )
                
                # Combine retrieved results
                result = "\n\n".join([result['text'] for result in results])
                confidence = sum(result['score'] for result in results) / len(results) if results else 0.0
                
                logger.info(f" Retrieved {len(results)} documents with avg confidence: {confidence:.2f}")
                
                return AgentOutput(
                    result=result,
                    confidence=confidence,
                    metadata={
                        "source": "researcher",
                        "retrieved_count": len(results),
                        "total_documents": len(doc_texts)
                    }
                )
                
            except Exception as e:
                logger.error(f" Error in RAG retrieval: {str(e)}")
                # Fallback: use all document texts
                combined_text = "\n\n".join(doc_texts)
                return AgentOutput(
                    result=combined_text,
                    confidence=0.6,
                    metadata={
                        "source": "researcher",
                        "method": "combined_fallback",
                        "error": f"RAG retrieval failed: {str(e)}"
                    }
                )
            
        except Exception as e:
            logger.error(f" Critical error in ResearcherAgent: {str(e)}", exc_info=True)
            return AgentOutput(
                result="", 
                confidence=0.0, 
                metadata={
                    "source": "researcher",
                    "error": f"Unexpected error: {str(e)}"
                }
            )