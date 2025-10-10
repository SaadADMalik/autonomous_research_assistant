from fastapi import FastAPI
from pydantic import BaseModel
from src.pipelines.orchestrator import Orchestrator
from src.data_fetcher import DataFetcher
import logging
from src.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI()

class SummaryRequest(BaseModel):
    query: str

@app.post("/generate_summary")
async def generate_summary(request: SummaryRequest):
    logger.info(f"Received query: {request.query}")
    try:
        orchestrator = Orchestrator()
        fetcher = DataFetcher()
        documents = await fetcher.fetch_arxiv(request.query, max_results=5)
        if not documents:
            logger.warning(f"No documents fetched for query: {request.query}")
            return {"result": "", "confidence": 0.0, "metadata": {"source": "orchestrator", "error": "No documents found"}}
        result = await orchestrator.run_pipeline(request.query, documents)
        return {"result": result.result, "confidence": result.confidence, "metadata": result.metadata}
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {"error": str(e)}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/status")
async def status_check():
    return {"progress": "Processing..."}