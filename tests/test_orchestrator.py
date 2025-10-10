import pytest
import logging
from fastapi.testclient import TestClient
from src.main import app
from src.pipelines.orchestrator import Orchestrator
from src.agents.base import AgentInput, AgentOutput
from src.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@pytest.fixture(scope="function")
def orchestrator():
    logger.info("Creating orchestrator fixture")
    return Orchestrator()

@pytest.fixture(scope="function")
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_health_endpoint(client):
    logger.info("Running test_health_endpoint")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_generate_summary_endpoint(client, mocker):
    logger.info("Running test_generate_summary_endpoint")
    mocker.patch(
        "src.data_fetcher.DataFetcher.fetch_arxiv",
        return_value=[
            "Quantum Computing Overview: Quantum computing leverages quantum mechanics to perform computations.",
            "Advances in Quantum Algorithms: New algorithms improve quantum system efficiency."
        ]
    )
    response = client.post("/generate_summary", json={"query": "Quantum Computing"})
    assert response.status_code == 200
    result = response.json()
    assert "result" in result
    assert "confidence" in result
    assert "metadata" in result
    assert result["confidence"] > 0.0
    assert result["metadata"].get("source") == "reviewer"

@pytest.mark.asyncio
async def test_orchestrator_pipeline(orchestrator):
    logger.info("Running test_orchestrator_pipeline")
    query = "AI advancements"
    documents = [
        "Artificial intelligence is a field of computer science focused on creating intelligent systems.",
        "Machine learning is a subset of artificial intelligence that enables systems to learn from data."
    ]
    result = await orchestrator.run_pipeline(query, documents)
    logger.info(f"Pipeline output: {result.result} (confidence: {result.confidence:.2f})")
    assert result.result, "Pipeline output is empty"
    assert result.confidence > 0.0, "Pipeline confidence is zero"
    assert result.metadata.get("source") == "reviewer", "Final output should come from reviewer"

@pytest.mark.asyncio
async def test_orchestrator_empty_query(orchestrator):
    logger.info("Running test_orchestrator_empty_query")
    query = ""
    documents = ["Test document."]
    result = await orchestrator.run_pipeline(query, documents)
    logger.info(f"Pipeline output for empty query: {result.result} (confidence: {result.confidence:.2f})")
    assert result.result == "", "Pipeline output should be empty for empty query"
    assert result.confidence == 0.0, "Pipeline confidence should be zero for empty query"
    assert "error" in result.metadata, "Error metadata should be present for empty query"

@pytest.mark.asyncio
async def test_orchestrator_no_documents(orchestrator):
    logger.info("Running test_orchestrator_no_documents")
    query = "AI advancements"
    documents = []
    result = await orchestrator.run_pipeline(query, documents)
    logger.info(f"Pipeline output for no documents: {result.result} (confidence: {result.confidence:.2f})")
    assert result.result == "", "Pipeline output should be empty for no documents"
    assert result.confidence == 0.0, "Pipeline confidence should be zero for no documents"
    assert "error" in result.metadata, "Error metadata should be present for no documents"

@pytest.mark.asyncio
async def test_orchestrator_low_confidence_retry(orchestrator, mocker):
    logger.info("Running test_orchestrator_low_confidence_retry")
    query = "AI advancements"
    documents = [
        "Artificial intelligence is a field of computer science focused on creating intelligent systems."
    ]
    mocker.patch(
        "src.agents.summarizer_agent.SummarizerAgent.run",
        return_value=AgentOutput(
            result="Mock summary",
            confidence=0.7,
            metadata={"source": "summarizer"}
        )
    )
    result = await orchestrator.run_pipeline(query, documents)
    logger.info(f"Pipeline output after retry: {result.result} (confidence: {result.confidence:.2f})")
    assert result.result == "Mock summary", "Pipeline output should be retry summary"
    assert result.confidence == 0.63, "Pipeline confidence should be penalized (0.7 * 0.9)"
    assert result.metadata.get("source") == "reviewer", "Final output should come from reviewer"
    assert result.metadata.get("retry") is True, "Retry metadata should be True"