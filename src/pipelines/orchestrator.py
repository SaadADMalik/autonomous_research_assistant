import logging
from typing import List, Union
from src.agents.researcher_agent import ResearcherAgent
from src.agents.summarizer_agent import SummarizerAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.utils.logger import setup_logging
from src.agents.base import AgentInput, AgentOutput

setup_logging()
logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        logger.info("Initializing Orchestrator")
        self.researcher = ResearcherAgent()
        self.summarizer = SummarizerAgent()
        self.reviewer = ReviewerAgent()

    async def run_pipeline(self, query: str, documents: List[Union[dict, str]]) -> AgentOutput:
        logger.info(f"Running pipeline with query: {query}")
        try:
            # Validate inputs
            if not query or not query.strip():
                logger.error("Empty query provided")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={"source": "orchestrator", "error": "Empty query"}
                )
            
            if not documents:
                logger.error("No documents provided")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={"source": "orchestrator", "error": "No documents provided"}
                )
            
            # Normalize documents to consistent format
            normalized_docs = []
            for doc in documents:
                if isinstance(doc, str):
                    # Convert string to dictionary format
                    normalized_doc = {
                        "title": "Text Document",
                        "summary": doc,
                        "url": "",
                        "year": 2025
                    }
                elif isinstance(doc, dict):
                    # Ensure dictionary has required fields
                    normalized_doc = {
                        "title": doc.get("title", "Untitled"),
                        "summary": doc.get("summary", doc.get("content", "")),
                        "url": doc.get("url", ""),
                        "year": doc.get("year", 2025)
                    }
                else:
                    logger.warning(f"Unexpected document type: {type(doc)}")
                    continue
                
                # Validate the document has content
                if normalized_doc["summary"]:
                    normalized_docs.append(normalized_doc)
            
            if not normalized_docs:
                logger.error("No valid documents after normalization")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={"source": "orchestrator", "error": "No valid documents"}
                )
            
            logger.info(f"Normalized {len(normalized_docs)} documents")
            
            # Step 1: Research phase - process and retrieve relevant content
            research_input = AgentInput(
                query=query, 
                metadata={"source": "orchestrator"}
            )
            
            logger.debug(f"Running researcher with {len(normalized_docs)} documents")
            research_output = await self.researcher.run(research_input, normalized_docs)
            
            if research_output.confidence == 0.0 or not research_output.result:
                logger.error("ResearcherAgent failed or returned empty result")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={"source": "orchestrator", "error": "Research phase failed"}
                )
            
            logger.info(f"Research phase completed with confidence {research_output.confidence:.2f}")
            
            # Step 2: Summarization phase
            summary_input = AgentInput(
                query=query,
                context=research_output.result,
                metadata={"source": "orchestrator"}
            )
            
            logger.debug("Running summarizer")
            summary_output = await self.summarizer.run(summary_input)
            
            if not summary_output.result:
                logger.error("SummarizerAgent returned empty result")
                return AgentOutput(
                    result="", 
                    confidence=0.0, 
                    metadata={"source": "orchestrator", "error": "Summarization failed"}
                )
            
            logger.info(f"Summarization completed with confidence {summary_output.confidence:.2f}")
            
            # Step 3: Review phase
            review_input = AgentInput(
                query=query,
                context=summary_output.result,
                metadata={"source": "orchestrator"}
            )
            
            logger.debug("Running reviewer")
            final_output = await self.reviewer.run(review_input, summary_output)
            
            # Ensure final output has proper metadata
            final_output.metadata.update({
                "source": "reviewer",
                "sources": [doc["url"] for doc in normalized_docs if doc.get("url")],
                "document_count": len(normalized_docs)
            })
            
            logger.info(f"Pipeline completed successfully with confidence {final_output.confidence:.2f}")
            return final_output
            
        except Exception as e:
            logger.error(f"Error in pipeline: {str(e)}", exc_info=True)
            return AgentOutput(
                result="", 
                confidence=0.0, 
                metadata={"source": "orchestrator", "error": str(e)}
            )