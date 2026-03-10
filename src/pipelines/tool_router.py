from typing import Dict, List


class ToolRouter:
    """Simple deterministic tool selection for the research workflow."""

    def route(self, query: str, documents: List[dict]) -> Dict[str, object]:
        query_lower = (query or "").lower()
        sources = {doc.get("source", "unknown") for doc in documents if isinstance(doc, dict)}

        selected_tools: List[str] = ["semantic_search", "summarization", "review"]

        if "semantic_scholar" in sources:
            selected_tools.append("citation_extraction")
        if any(keyword in query_lower for keyword in ["survey", "landscape", "compare", "trend"]):
            selected_tools.append("paper_clustering")

        selected_tools.append("report_generation")

        return {
            "selected_tools": selected_tools,
            "source_preference": sorted(sources),
            "strategy": "deterministic_rule_router",
        }
