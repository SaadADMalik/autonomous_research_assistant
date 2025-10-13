import logging
from typing import List
from src.rag.pipeline import RAGPipeline
from .base import AgentInput, AgentOutput
from src.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class ResearcherAgent:
    def __init__(self):
        logger.info("Initializing ResearcherAgent")
        self.rag_pipeline = RAGPipeline()

    async def run(self, input_data: AgentInput, documents: List[str] = None) -> AgentOutput:
        logger.info(f"Running ResearcherAgent with query: {input_data.query}")
        try:
            doc_texts = [doc["summary"] if isinstance(doc, dict) else doc for doc in documents] if documents else []
            logger.debug(f"Received {len(doc_texts)} documents: {[text[:50] + '...' for text in doc_texts[:2]]}")

            if doc_texts:
                logger.info(f"Storing {len(doc_texts)} documents")
                metadata = [input_data.metadata] * len(doc_texts) if input_data.metadata else [{"source": "researcher"}] * len(doc_texts)
                logger.debug(f"Metadata for storage: {metadata[:2]}")
                ids = await self.rag_pipeline.process_and_store(doc_texts, metadata=metadata)
                if not ids:
                    logger.warning("Failed to store documents in RAG pipeline")
                    return AgentOutput(result="", confidence=0.0, metadata={"source": "researcher", "error": "Failed to store documents"})
                logger.info(f"Stored {len(ids)} chunks")

            logger.debug(f"Retrieving relevant documents for query: {input_data.query}")
            results = await self.rag_pipeline.retrieve_relevant(
                query=input_data.query,
                k=3,
                threshold=0.1
            )
            
            if not results:
                logger.warning("No relevant documents retrieved")
                return AgentOutput(result="", confidence=0.0, metadata={"source": "researcher", "error": "No relevant documents found"})
            
            result = "\n".join([result['text'] for result in results])
            confidence = sum(result['score'] for result in results) / len(results)
            logger.info(f"Retrieved {len(results)} documents with average confidence: {confidence:.2f}")
            return AgentOutput(
                result=result,
                confidence=confidence,
                metadata={"source": "researcher", "retrieved_count": len(results)}
            )
        except Exception as e:
            logger.error(f"Error in ResearcherAgent: {str(e)}")
            return AgentOutput(result="", confidence=0.0, metadata={"source": "researcher", "error": str(e)})