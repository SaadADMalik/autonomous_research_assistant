import logging
from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np
from ..utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class EmbeddingModel:
    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        logger.info(f"🧠 Initializing EmbeddingModel with {model_name}")
        self.model_name = model_name
        self.model = None
        
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"✅ Model loaded successfully: {model_name}")
        except Exception as e:
            logger.error(f"❌ Failed to load model {model_name}: {str(e)}")
            logger.info("⚠️ Attempting fallback model...")
            
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")  # Lighter model
                logger.info("✅ Fallback model loaded: all-MiniLM-L6-v2")
            except Exception as fallback_error:
                logger.error(f"❌ Fallback model also failed: {str(fallback_error)}")
                self.model = None

    def _is_valid_model(self) -> bool:
        """Check if model is properly initialized."""
        if self.model is None:
            logger.error("❌ Embedding model not initialized")
            return False
        return True

    def embed_text(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embeddings for text.
        Returns normalized embeddings or empty array on failure.
        """
        try:
            if not self._is_valid_model():
                logger.error("❌ Cannot embed: model not initialized")
                return np.array([])
            
            # Validate input
            if isinstance(text, str):
                if not text or not text.strip():
                    logger.warning("⚠️ Empty string provided for embedding")
                    return np.array([])
                text = [text.strip()]
            elif isinstance(text, list):
                if not text:
                    logger.warning("⚠️ Empty list provided for embedding")
                    return np.array([])
                # Clean and filter empty strings
                text = [t.strip() for t in text if t and t.strip()]
                if not text:
                    logger.warning("⚠️ All inputs were empty after cleaning")
                    return np.array([])
            else:
                logger.error(f"❌ Invalid input type: {type(text)}")
                return np.array([])
            
            logger.debug(f"📊 Embedding {len(text)} text(s)")
            
            try:
                embeddings = self.model.encode(
                    text,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    batch_size=32
                )
                
                # Validate output
                if embeddings is None or len(embeddings) == 0:
                    logger.error("❌ Model returned empty embeddings")
                    return np.array([])
                
                # Ensure proper normalization
                if len(embeddings.shape) == 1:
                    # Single embedding
                    norm = np.linalg.norm(embeddings)
                    if norm > 0:
                        embeddings = embeddings / norm
                else:
                    # Multiple embeddings
                    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                    embeddings = embeddings / norms
                
                logger.debug(f"✅ Generated embeddings shape: {embeddings.shape}")
                return embeddings
                
            except RuntimeError as e:
                logger.error(f"❌ Model inference error: {str(e)}")
                return np.array([])
            except Exception as e:
                logger.error(f"❌ Embedding generation failed: {str(e)}")
                return np.array([])
                
        except Exception as e:
            logger.error(f"❌ Critical error in embed_text: {str(e)}", exc_info=True)
            return np.array([])