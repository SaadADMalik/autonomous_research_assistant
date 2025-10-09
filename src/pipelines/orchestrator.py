import logging
from typing import List
from src.agents.researcher_agent import ResearcherAgent
from src.agents.summarizer_agent import SummarizerAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.base import AgentInput, AgentOutput

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        self.researcher = ResearcherAgent()
        self.summarizer = SummarizerAgent()
        self.reviewer = ReviewerAgent()

    async def run_pipeline(self, query: str, documents: List[str] = None) -> AgentOutput:
        logger.info(f"Running pipeline with query: {query}")
        try:
            # Step 1: Research
            research_input = AgentInput(query=query)
            research_output = await self.researcher.run(research_input, documents)
            if research_output.confidence == 0.0:
                logger.error("ResearcherAgent failed")
                return AgentOutput(result="", confidence=0.0, metadata={"source": "orchestrator", "error": "Research failed"})
            
            # Step 2: Summarize
            summary_input = AgentInput(
                query=query,
                context=research_output.result,
                metadata=research_output.metadata
            )
            summary_output = await self.summarizer.run(summary_input)
            if summary_output.confidence == 0.0:
                logger.error("SummarizerAgent failed")
                return AgentOutput(result="", confidence=0.0, metadata={"source": "orchestrator", "error": "Summarization failed"})
            
            # Step 3: Review
            review_input = AgentInput(
                query=query,
                context=summary_output.result,
                metadata=summary_output.metadata
            )
            review_output = await self.reviewer.run(review_input, previous_output=summary_output)
            if review_output.confidence == 0.0:
                logger.error("ReviewerAgent failed")
                return AgentOutput(result="", confidence=0.0, metadata={"source": "orchestrator", "error": "Review failed"})
            
            logger.info(f"Pipeline completed with final confidence: {review_output.confidence:.2f}")
            return review_output
        except Exception as e:
            logger.error(f"Error in pipeline: {str(e)}")
            return AgentOutput(result="", confidence=0.0, metadata={"source": "orchestrator", "error": str(e)})