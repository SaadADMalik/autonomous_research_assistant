import pytest
import logging
import numpy as np
from src.rag.embeddings import EmbeddingModel
from src.rag.vectorstore import VectorStore
from src.rag.pipeline import RAGPipeline
from src.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@pytest.fixture(scope="function")
def embedding_model():
    logger.info("Creating embedding_model fixture")
    return EmbeddingModel()

@pytest.fixture(scope="function")
def vector_store():
    logger.info("Creating vector_store fixture")
    vs = VectorStore(persist_dir="D:/autonomous_research_assistant/data/vectorstore")
    # Clean start - collection is already recreated in __init__
    yield vs
    # Cleanup after test - delete and recreate for next test
    try:
        vs.delete_collection()
        logger.info("Cleaned up vector_store fixture")
    except Exception as e:
        logger.warning(f"Cleanup warning: {e}")

@pytest.mark.asyncio
async def test_embedding_model(embedding_model):
    logger.info("Running test_embedding_model")
    text = "This is a test sentence."
    embeddings = embedding_model.embed_text(text)
    assert embeddings.shape[0] == 768  # all-mpnet-base-v2 dimension
    assert np.allclose(np.linalg.norm(embeddings), 1.0, atol=1e-5), "Embedding not normalized"

@pytest.mark.asyncio
async def test_vectorstore_operations(vector_store, embedding_model):
    logger.info("Running test_vectorstore_operations")
    documents = ["This is a test document.", "This is another test document."]
    metadata = [{"source": "test"}, {"source": "test"}]
    ids = await vector_store.add_texts(documents, metadata)
    assert len(ids) == len(documents), "Not all documents were added"
    
    # Generate embedding for the query BEFORE searching
    query_embedding = embedding_model.embed_text("test query")
    results = await vector_store.similarity_search(query_embedding, k=2, threshold=0.0)
    assert len(results) == 2, "Did not retrieve expected number of documents"
    assert all(doc in documents for doc in [result['text'] for result in results]), "Retrieved documents do not match"

@pytest.mark.asyncio
async def test_rag_pipeline():
    logger.info("Running test_rag_pipeline")
    pipeline = RAGPipeline()
    documents = ["This is a test document.", "This is another test document."]
    metadata = [{"source": "test"}, {"source": "test"}]
    
    ids = await pipeline.process_and_store(documents, metadata)
    assert len(ids) == len(documents), "Not all documents were stored"
    
    results = await pipeline.retrieve_relevant("test query", k=2, threshold=0.0)
    assert len(results) == 2, "Did not retrieve expected number of documents"
    assert all(doc in documents for doc in [result['text'] for result in results]), "Retrieved documents do not match"