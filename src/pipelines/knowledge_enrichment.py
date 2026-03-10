import math
import re
from collections import Counter
from typing import Dict, List


class PaperClusterer:
    """Clusters papers using lightweight token-vector cosine similarity."""

    STOPWORDS = {
        "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with", "by", "is", "are",
        "this", "that", "from", "as", "at", "we", "our", "their", "be", "was", "were", "it",
    }

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r"[a-zA-Z]{3,}", (text or "").lower())
        return [token for token in tokens if token not in self.STOPWORDS]

    def _vectorize(self, text: str) -> Counter:
        return Counter(self._tokenize(text))

    def _cosine(self, v1: Counter, v2: Counter) -> float:
        if not v1 or not v2:
            return 0.0
        common = set(v1).intersection(v2)
        numerator = sum(v1[token] * v2[token] for token in common)
        d1 = math.sqrt(sum(value * value for value in v1.values()))
        d2 = math.sqrt(sum(value * value for value in v2.values()))
        if d1 == 0 or d2 == 0:
            return 0.0
        return numerator / (d1 * d2)

    def cluster(self, documents: List[dict], threshold: float = 0.25) -> List[Dict[str, object]]:
        vectors = []
        entries = []
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            text = f"{doc.get('title', '')} {doc.get('summary', '')}".strip()
            vector = self._vectorize(text)
            if not vector:
                continue
            vectors.append(vector)
            entries.append(doc)

        clusters: List[Dict[str, object]] = []
        for idx, vector in enumerate(vectors):
            placed = False
            for cluster in clusters:
                score = self._cosine(vector, cluster["centroid"])
                if score >= threshold:
                    cluster["items"].append(entries[idx])
                    cluster["centroid"].update(vector)
                    placed = True
                    break
            if not placed:
                clusters.append({"centroid": Counter(vector), "items": [entries[idx]]})

        result = []
        for cluster_id, cluster in enumerate(clusters, start=1):
            top_terms = [term for term, _ in cluster["centroid"].most_common(5)]
            result.append(
                {
                    "cluster_id": cluster_id,
                    "paper_count": len(cluster["items"]),
                    "themes": top_terms,
                    "titles": [item.get("title", "Untitled") for item in cluster["items"]],
                }
            )
        return result


class CitationExtractor:
    """Extracts lightweight normalized citation objects from paper metadata."""

    def extract(self, documents: List[dict]) -> List[Dict[str, object]]:
        citations: List[Dict[str, object]] = []
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            authors = doc.get("authors") or []
            author_text = ", ".join(authors[:3]) if isinstance(authors, list) else str(authors)
            citations.append(
                {
                    "title": doc.get("title", "Untitled"),
                    "authors": authors,
                    "year": doc.get("year"),
                    "venue": doc.get("venue", ""),
                    "url": doc.get("url", ""),
                    "citations": doc.get("citations", 0),
                    "formatted": f"{author_text} ({doc.get('year', 'n.d.')}). {doc.get('title', 'Untitled')}. {doc.get('venue', '')}. {doc.get('url', '')}".strip(),
                }
            )
        return citations


class ReportGenerator:
    """Generates a research report in markdown."""

    def generate(
        self,
        query: str,
        summary: str,
        clusters: List[Dict[str, object]],
        citations: List[Dict[str, object]],
        confidence: float,
    ) -> str:
        lines: List[str] = []
        lines.append(f"# Research Report: {query}")
        lines.append("")
        lines.append("## Executive Summary")
        lines.append(summary or "No summary available.")
        lines.append("")
        lines.append("## Confidence")
        lines.append(f"Overall confidence: {confidence:.2f}")
        lines.append("")
        lines.append("## Paper Clusters")
        if clusters:
            for cluster in clusters:
                lines.append(f"- Cluster {cluster['cluster_id']} ({cluster['paper_count']} papers): {', '.join(cluster['themes'])}")
        else:
            lines.append("- No clusters generated.")
        lines.append("")
        lines.append("## Citations")
        if citations:
            for citation in citations[:20]:
                lines.append(f"- {citation['formatted']}")
        else:
            lines.append("- No citations extracted.")
        return "\n".join(lines)
