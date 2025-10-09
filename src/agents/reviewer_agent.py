import logging
from .base import AgentInput, AgentOutput
from .summarizer_agent import SummarizerAgent

logger = logging.getLogger(__name__)

class ReviewerAgent:
    def __init__(self, confidence_threshold: float = 0.8):
        self.confidence_threshold = confidence_threshold
        self.summarizer = SummarizerAgent()

    async def run(self, input_data: AgentInput, previous_output: AgentOutput = None) -> AgentOutput:
        logger.info(f"Running ReviewerAgent with query: {input_data.query}")
        try:
            if not input_data.context:
                logger.warning("No context provided for review")
                return AgentOutput(result="", confidence=0.0, metadata={"source": "reviewer"})
            
            # Use confidence from previous_output (e.g., from SummarizerAgent)
            confidence = previous_output.confidence if previous_output and previous_output.confidence is not None else 0.5
            result = input_data.context
            
            if confidence < self.confidence_threshold:
                logger.info(f"Confidence {confidence:.2f} below threshold {self.confidence_threshold}. Retrying summarization.")
                # Retry with adjusted prompt
                adjusted_input = AgentInput(
                    query=input_data.query + " (Be more concise)",
                    context=input_data.context,
                    metadata=input_data.metadata
                )
                retry_output = await self.summarizer.run(adjusted_input)
                result = retry_output.result
                confidence = retry_output.confidence * 0.9  # Slightly penalize retry
                logger.info(f"Retry produced summary: {result[:50]}... with confidence: {confidence:.2f}")
            
            return AgentOutput(
                result=result,
                confidence=confidence,
                metadata={"source": "reviewer", "retry": confidence < self.confidence_threshold}
            )
        except Exception as e:
            logger.error(f"Error in ReviewerAgent: {str(e)}")
            return AgentOutput(result="", confidence=0.0, metadata={"source": "reviewer", "error": str(e)})