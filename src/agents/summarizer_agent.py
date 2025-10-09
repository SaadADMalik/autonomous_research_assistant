import logging
from .base import AgentInput, AgentOutput
from transformers import pipeline
import torch

logger = logging.getLogger(__name__)

class SummarizerAgent:
    def __init__(self):
        logger.info("Initializing SummarizerAgent with BART model")
        self.device = 0 if torch.cuda.is_available() else -1  # Use GPU if available, else CPU
        self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn", device=self.device)

    async def run(self, input_data: AgentInput) -> AgentOutput:
        logger.info(f"Running SummarizerAgent with query: {input_data.query}")
        try:
            if not input_data.context:
                logger.warning("No context provided for summarization")
                return AgentOutput(result="", confidence=0.0, metadata={"source": "summarizer"})
            
            # Estimate input length (approximate token count)
            input_length = len(input_data.context.split())
            max_length = min(130, max(30, input_length // 2))  # Dynamic max_length: half input or 130
            min_length = min(30, max(10, input_length // 4))  # Dynamic min_length: quarter input or 30
            
            # Real summarization using BART model
            summary = self.summarizer(
                input_data.context,
                max_length=max_length,
                min_length=min_length,
                do_sample=False
            )[0]['summary_text']
            confidence = 0.9  # Mock confidence; in real scenarios, use model confidence if available
            logger.info(f"SummarizerAgent produced summary: {summary[:50]}...")
            return AgentOutput(
                result=summary,
                confidence=confidence,
                metadata={"source": "summarizer"}
            )
        except Exception as e:
            logger.error(f"Error in SummarizerAgent: {str(e)}")
            return AgentOutput(result="", confidence=0.0, metadata={"source": "summarizer", "error": str(e)})