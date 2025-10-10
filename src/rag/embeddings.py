import logging
from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np
from ..utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

class EmbeddingModel:
    def __init__(self, model_name: str = "all-mpnet-base-v2"):  # Using all-mpnet-base-v2
        logger.info(f"Initializing EmbeddingModel with {model_name}")
        self.model = SentenceTransformer(model_name)

    def embed_text(self, text: Union[str, List[str]]) -> np.ndarray:
        try:
            embeddings = self.model.encode(
                text,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=32
            )
            # Explicit normalization to ensure norm=1.0
            if len(embeddings.shape) == 1:
                norm = np.linalg.norm(embeddings)
                embeddings = embeddings / norm if norm != 0 else embeddings
            else:
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                embeddings = embeddings / norms
            logger.info(f"Embedding norm after normalization: {np.linalg.norm(embeddings[0]) if len(embeddings.shape) > 1 else np.linalg.norm(embeddings)}")
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            return np.array([])