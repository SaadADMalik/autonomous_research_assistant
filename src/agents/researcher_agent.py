import logging
from typing import List
from src.rag.pipeline import RAGPipeline
from .base import AgentInput, AgentOutput

logger = logging.getLogger(__name__)

class ResearcherAgent:
    def __init__(self):
        self.rag_pipeline = RAGPipeline()

    async def run(self, input_data: AgentInput, documents: List[str] = None) -> AgentOutput:
        logger.info(f"Running ResearcherAgent with query: {input_data.query}")
        try:
            # Store documents if provided
            if documents:
                logger.info(f"Storing {len(documents)} documents")
                # Provide default metadata if none is provided
                metadata = [input_data.metadata] * len(documents) if input_data.metadata else [{"source": "researcher"}] * len(documents)
                ids = await self.rag_pipeline.process_and_store(documents, metadata=metadata)
                if not ids:
                    logger.warning("Failed to store documents")
            
            # Retrieve relevant documents
            results = await self.rag_pipeline.retrieve_relevant(
                query=input_data.query,
                k=3,
                threshold=0.4  # Lowered from 0.5 to capture more documents (e.g., 0.46 score)
            )
            
            if not results:
                logger.warning("No relevant documents found")
                return AgentOutput(result="", confidence=0.0, metadata={"source": "researcher"})
            
            # Combine retrieved texts
            result = "\n".join([result['text'] for result in results])
            # Average confidence from similarity scores
            confidence = sum(result['score'] for result in results) / len(results)
            logger.info(f"ResearcherAgent retrieved {len(results)} documents with average confidence: {confidence:.2f}")
            return AgentOutput(
                result=result,
                confidence=confidence,
                metadata={"source": "researcher", "retrieved_count": len(results)}
            )
        except Exception as e:
            logger.error(f"Error in ResearcherAgent: {str(e)}")
            return AgentOutput(result="", confidence=0.0, metadata={"source": "researcher", "error": str(e)})