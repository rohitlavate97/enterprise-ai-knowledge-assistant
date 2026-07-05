"""Service for local vector embeddings generation using SentenceTransformers."""

import logging

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service layer coordinating HuggingFace SentenceTransformer models."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        self.dimension = 384  # Dimension of all-MiniLM-L6-v2 vectors

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-loaded SentenceTransformer instance."""
        if self._model is None:
            logger.info(
                "Loading SentenceTransformer model: %s", self.model_name
            )
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate dense vector embeddings for a list of text snippets."""
        if not texts:
            return []
        embeddings = self.model.encode(texts, show_progress_bar=False)
        # Convert numpy float arrays to standard Python float lists
        return [e.tolist() for e in embeddings]


embedding_service = EmbeddingService()
