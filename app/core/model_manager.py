"""
Model Manager - Lazy-load singleton for Hugging Face models
CPU-only, with caching and fallback support
"""

from typing import Optional, Dict, Any, List
from sentence_transformers import SentenceTransformer, CrossEncoder
from transformers import pipeline, Pipeline
import logging

logger = logging.getLogger(__name__)

# Model IDs
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
NER_MODEL = "dslim/bert-base-NER"
SUMMARIZATION_MODEL = "sshleifer/distilbart-cnn-12-6"
GENERATOR_MODEL = "google/flan-t5-small"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Global model cache
_models: Dict[str, Any] = {}


class ModelManager:
    """Singleton manager for all Hugging Face models"""
    
    _instance: Optional['ModelManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.device = "cpu"
        self.batch_size = 5
        logger.info(f"ModelManager initialized (device={self.device}, batch_size={self.batch_size})")
    
    def get_embedding_model(self) -> SentenceTransformer:
        """Get sentence embedding model (MiniLM)"""
        if 'embedding' not in _models:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            try:
                model = SentenceTransformer(EMBEDDING_MODEL, device=self.device)
                _models['embedding'] = model
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
        return _models['embedding']
    
    def get_ner_pipeline(self) -> Pipeline:
        """Get NER pipeline (BERT-base-NER)"""
        if 'ner' not in _models:
            logger.info(f"Loading NER model: {NER_MODEL}")
            try:
                ner_pipeline = pipeline(  # type: ignore
                    "ner",
                    model=NER_MODEL,
                    tokenizer=NER_MODEL,
                    device=self.device,
                    aggregation_strategy="simple"
                )
                _models['ner'] = ner_pipeline
                logger.info("NER model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load NER model: {e}")
                raise
        return _models['ner']
    
    def get_summarization_pipeline(self) -> Pipeline:
        """Get summarization pipeline (DistilBART)"""
        if 'summarization' not in _models:
            logger.info(f"Loading summarization model: {SUMMARIZATION_MODEL}")
            try:
                sum_pipeline = pipeline(
                    "summarization",
                    model=SUMMARIZATION_MODEL,
                    tokenizer=SUMMARIZATION_MODEL,
                    device=self.device
                )
                _models['summarization'] = sum_pipeline
                logger.info("Summarization model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load summarization model: {e}")
                raise
        return _models['summarization']
    
    def get_generator_pipeline(self) -> Pipeline:
        """Get text generation pipeline (Flan-T5-small)"""
        if 'generator' not in _models:
            logger.info(f"Loading generator model: {GENERATOR_MODEL}")
            try:
                gen_pipeline = pipeline(
                    "text2text-generation",
                    model=GENERATOR_MODEL,
                    tokenizer=GENERATOR_MODEL,
                    device=self.device,
                    max_new_tokens=80
                )
                _models['generator'] = gen_pipeline
                logger.info("Generator model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load generator model: {e}")
                raise
        return _models['generator']
    
    def get_reranker_model(self) -> CrossEncoder:
        """Get cross-encoder reranker (MiniLM)"""
        if 'reranker' not in _models:
            logger.info(f"Loading reranker model: {RERANKER_MODEL}")
            try:
                reranker = CrossEncoder(RERANKER_MODEL, device=self.device)
                _models['reranker'] = reranker
                logger.info("Reranker model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load reranker model: {e}")
                raise
        return _models['reranker']
    
    def embed_texts(self, texts: List[str], batch_size: Optional[int] = None) -> List[List[float]]:
        """
        Embed texts using MiniLM
        Returns embeddings of dimension 384 (MiniLM default)
        """
        model = self.get_embedding_model()
        batch_size = batch_size or self.batch_size
        try:
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            # Fallback: return zero vectors with correct dimension (384 for MiniLM)
            return [[0.0] * 384] * len(texts)
    
    def summarize_text(self, text: str, max_length: int = 80) -> str:
        """Summarize text using DistilBART"""
        pipeline = self.get_summarization_pipeline()
        try:
            result = pipeline(
                text,
                max_length=max_length,
                min_length=20,
                do_sample=False,
                truncation=True
            )
            return result[0]['summary_text']  # type: ignore
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return text[:200] + "..."
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities using BERT-NER"""
        pipeline = self.get_ner_pipeline()
        try:
            entities = pipeline(text)  # type: ignore
            return entities  # type: ignore
        except Exception as e:
            logger.error(f"NER failed: {e}")
            return []
    
    def generate_text(self, prompt: str, max_new_tokens: int = 80) -> str:
        """Generate text using Flan-T5"""
        pipeline = self.get_generator_pipeline()
        try:
            result = pipeline(
                prompt,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                truncation=True
            )
            return result[0]['generated_text']  # type: ignore
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return ""
    
    def rerank(self, query: str, documents: List[str]) -> List[float]:
        """Rerank documents using cross-encoder"""
        reranker = self.get_reranker_model()
        try:
            pairs = [[query, doc] for doc in documents]
            scores = reranker.predict(pairs)
            return scores.tolist()
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return [0.0] * len(documents)
    
    def clear_cache(self):
        """Clear all cached models"""
        global _models
        _models.clear()
        logger.info("Model cache cleared")


# Singleton instance
model_manager = ModelManager()
