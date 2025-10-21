"""
Model Manager - Placeholder for backward compatibility
All AI functionality now uses GPT-4o-mini via LLM provider
"""

import logging

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Deprecated ModelManager - kept for backward compatibility
    All AI functionality now delegated to GPT-4o-mini via llm_provider
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        logger.info("ModelManager initialized (deprecated - using GPT-4o-mini)")
    
    def embed_texts(self, texts):
        """Deprecated - embeddings no longer used"""
        logger.warning("embed_texts called but embeddings are deprecated")
        # Return zero vectors for backward compatibility
        return [[0.0] * 384 for _ in texts]
    
    def extract_entities(self, text):
        """Deprecated - NER no longer used"""
        logger.warning("extract_entities called but NER is deprecated")
        return []
    
    def summarize_text(self, text, max_length=80):
        """Deprecated - use llm_provider instead"""
        logger.warning("summarize_text called but DistilBART is deprecated")
        return text[:200] + "..."
    
    def generate_text(self, prompt, max_new_tokens=80):
        """Deprecated - use llm_provider instead"""
        logger.warning("generate_text called but Flan-T5 is deprecated")
        return "Deprecated model output"
    
    def rerank(self, query, documents):
        """Deprecated - reranking no longer used"""
        logger.warning("rerank called but cross-encoder is deprecated")
        return [0.5] * len(documents)


# Global singleton instance
model_manager = ModelManager()
