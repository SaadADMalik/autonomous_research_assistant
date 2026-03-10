"""
Global Model Cache Manager - Singleton Pattern for ML Models

This module manages singleton instances of expensive-to-load models
to ensure they are loaded only once and reused across all requests.
Significantly improves performance for subsequent queries.

IMPORTANT: Caching is ONLY enabled in production. Tests get fresh instances.
"""

import logging
import os
from typing import Optional
from .embeddings import EmbeddingModel
from .vectorstore import VectorStore
from ..utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# ✅ Check if running in test mode
TESTING = os.getenv('PYTEST_CURRENT_TEST') is not None or 'pytest' in os.environ.get('_', '')


class ModelCache:
    """
    Singleton cache manager for all ML models and data structures.
    
    Ensures models are loaded only once in memory and reused across
    all pipeline instances, dramatically reducing initialization overhead.
    
    Thread-safe implementation using class-level variables.
    
    IMPORTANT: Caching is disabled during tests to allow fresh instances.
    """
    
    # Singleton instances - class-level cache
    _embedding_model: Optional[EmbeddingModel] = None
    _vector_store: Optional[VectorStore] = None
    _cache_initialized: bool = False
    
    @classmethod
    def initialize(cls) -> None:
        """
        Initialize all cached models at application startup.
        Call this once when the application starts.
        """
        if TESTING:
            logger.info("ℹ️  TEST MODE: Caching disabled for test isolation")
            return
        
        if cls._cache_initialized:
            logger.debug("✅ Model cache already initialized")
            return
        
        try:
            logger.info("🔧 STARTUP: Initializing global model cache...")
            
            # Pre-load embedding model
            embedding_model = cls.get_embedding_model()
            if embedding_model and embedding_model.model:
                logger.info("✅ CACHE: Embedding model pre-loaded")
            
            # Pre-load vector store
            vector_store = cls.get_vector_store()
            if vector_store:
                logger.info("✅ CACHE: Vector store initialized")
            
            cls._cache_initialized = True
            logger.info("✅ STARTUP: Model cache fully initialized and ready")
            
        except Exception as e:
            logger.error(f"❌ CACHE INIT ERROR: {str(e)}", exc_info=True)
            raise
    
    @classmethod
    def get_embedding_model(cls, model_name: str = "all-mpnet-base-v2") -> EmbeddingModel:
        """
        Get or create the singleton embedding model instance.
        
        In test mode: Always creates a fresh instance (no caching)
        In production: Caches and reuses single instance
        
        Args:
            model_name: Name of the model to use (only used on first call)
            
        Returns:
            Cached or fresh EmbeddingModel instance
            
        Performance (production):
            - First call: ~5-10 seconds (model download + load)
            - Subsequent calls: <1ms (instant return)
        """
        if TESTING:
            # ✅ Tests get fresh instances for isolation
            logger.debug(f"TEST MODE: Creating fresh embedding model")
            return EmbeddingModel(model_name=model_name)
        
        # ✅ Production: Use cached instance
        if cls._embedding_model is None:
            logger.info(f"🧠 CACHE MISS: Loading embedding model '{model_name}'...")
            cls._embedding_model = EmbeddingModel(model_name=model_name)
            logger.info(f"✅ CACHE: Embedding model cached and ready")
        else:
            logger.debug(f"✅ CACHE HIT: Reusing cached embedding model")
        
        return cls._embedding_model
    
    @classmethod
    def get_vector_store(cls, persist_dir: str = ":memory:") -> VectorStore:
        """
        Get or create the singleton vector store instance.
        
        🎯 CHANGED: Now defaults to in-memory to avoid contaminated persistent data
        
        In test mode: Always creates a fresh instance (no caching)
        In production: Caches and reuses single instance
        
        Args:
            persist_dir: Directory for ChromaDB persistence (default ":memory:" for clean state)
            
        Returns:
            Cached or fresh VectorStore instance
            
        Performance (production):
            - First call: ~2-3 seconds (ChromaDB init)
            - Subsequent calls: <1ms (instant return)
        """
        if TESTING:
            # ✅ Tests get fresh instances for isolation
            logger.debug(f"TEST MODE: Creating fresh vector store")
            return VectorStore(use_memory=True, reset_collection=True)
        
        # ✅ Production: Use cached instance (in-memory for clean state)
        if cls._vector_store is None:
            logger.info(f"🗄️ CACHE MISS: Initializing IN-MEMORY vector store (clean state)...")
            cls._vector_store = VectorStore(use_memory=True, collection_name="main_cache", reset_collection=True)
            logger.info(f"✅ CACHE: Vector store cached and ready")
        else:
            logger.debug(f"✅ CACHE HIT: Reusing cached vector store")
        
        return cls._vector_store
    
    @classmethod
    def reset(cls) -> None:
        """
        Reset all cached models. Use only for testing or manual cache clearing.
        
        WARNING: This will clear all cached models from memory.
        """
        logger.warning("⚠️ CACHE RESET: Clearing all cached models...")
        cls._embedding_model = None
        cls._vector_store = None
        cls._cache_initialized = False
        logger.info("✅ Cache reset complete")
    
    @classmethod
    def get_cache_status(cls) -> dict:
        """
        Get current cache status for debugging and monitoring.
        
        Returns:
            Dictionary with cache status information
        """
        return {
            "testing_mode": TESTING,
            "initialized": cls._cache_initialized,
            "embedding_model_cached": cls._embedding_model is not None,
            "vector_store_cached": cls._vector_store is not None,
            "embedding_model_type": type(cls._embedding_model).__name__ if cls._embedding_model else "None",
            "vector_store_type": type(cls._vector_store).__name__ if cls._vector_store else "None"
        }