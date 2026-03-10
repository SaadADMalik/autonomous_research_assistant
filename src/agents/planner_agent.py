import logging
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    name: str
    description: str
    required: bool = True


class PlannerAgent:
    """Builds a lightweight execution plan for research workflows."""

    def create_plan(self, query: str) -> Dict[str, object]:
        query_lower = (query or "").lower()

        include_literature_search = True
        include_clustering = any(keyword in query_lower for keyword in ["trend", "landscape", "compare", "survey", "map"])
        include_citation_extraction = True
        include_report_generation = True

        steps: List[PlanStep] = [
            PlanStep("literature_search", "Fetch and normalize papers from research sources", True),
            PlanStep("retrieval_and_summarization", "Retrieve relevant evidence and produce synthesis", True),
            PlanStep("quality_review", "Validate coherence and confidence", True),
            PlanStep("paper_clustering", "Group related papers by semantic similarity", include_clustering),
            PlanStep("citation_extraction", "Extract normalized citation records", include_citation_extraction),
            PlanStep("report_generation", "Generate a structured research report", include_report_generation),
        ]

        active_steps = [s.__dict__ for s in steps if s.required]

        logger.info("Planner created %d active steps for query '%s'", len(active_steps), query)
        return {
            "query": query,
            "active_steps": active_steps,
            "capabilities": {
                "literature_search": include_literature_search,
                "paper_clustering": include_clustering,
                "summarization": True,
                "citation_extraction": include_citation_extraction,
                "report_generation": include_report_generation,
            },
        }
