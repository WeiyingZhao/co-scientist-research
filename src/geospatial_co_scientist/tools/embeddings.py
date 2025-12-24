"""Embedding tools for similarity computation and vector operations."""

import logging
from typing import Optional

import numpy as np
from pydantic import BaseModel

from geospatial_co_scientist.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingTool:
    """Tool for computing text embeddings."""

    def __init__(self, model_name: Optional[str] = None):
        self.settings = get_settings()
        self.model_name = model_name or self.settings.embedding_model
        self._model = None
        self._embeddings = None

    def _get_openai_embeddings(self):
        """Get OpenAI embeddings instance."""
        if self._embeddings is None:
            from langchain_openai import OpenAIEmbeddings
            self._embeddings = OpenAIEmbeddings(
                model=self.model_name,
                openai_api_key=self.settings.openai_api_key
            )
        return self._embeddings

    def _get_sentence_transformer(self):
        """Get SentenceTransformer model for local embeddings."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
            except ImportError:
                logger.warning("sentence-transformers not installed")
                return None
        return self._model

    async def embed_text(self, text: str) -> list[float]:
        """
        Compute embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        try:
            embeddings = self._get_openai_embeddings()
            vector = await embeddings.aembed_query(text)
            return vector
        except Exception as e:
            logger.warning(f"OpenAI embedding failed: {e}, trying local model")
            model = self._get_sentence_transformer()
            if model:
                vector = model.encode(text).tolist()
                return vector
            raise

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Compute embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self._get_openai_embeddings()
            vectors = await embeddings.aembed_documents(texts)
            return vectors
        except Exception as e:
            logger.warning(f"OpenAI batch embedding failed: {e}, trying local model")
            model = self._get_sentence_transformer()
            if model:
                vectors = model.encode(texts).tolist()
                return vectors
            raise

    def embed_text_sync(self, text: str) -> list[float]:
        """Synchronous version of embed_text."""
        try:
            embeddings = self._get_openai_embeddings()
            vector = embeddings.embed_query(text)
            return vector
        except Exception as e:
            logger.warning(f"OpenAI embedding failed: {e}, trying local model")
            model = self._get_sentence_transformer()
            if model:
                vector = model.encode(text).tolist()
                return vector
            raise

    def embed_texts_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous version of embed_texts."""
        try:
            embeddings = self._get_openai_embeddings()
            vectors = embeddings.embed_documents(texts)
            return vectors
        except Exception as e:
            logger.warning(f"OpenAI batch embedding failed: {e}, trying local model")
            model = self._get_sentence_transformer()
            if model:
                vectors = model.encode(texts).tolist()
                return vectors
            raise


def compute_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Cosine similarity score (0 to 1)
    """
    arr1 = np.array(vec1)
    arr2 = np.array(vec2)

    dot_product = np.dot(arr1, arr2)
    norm1 = np.linalg.norm(arr1)
    norm2 = np.linalg.norm(arr2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = dot_product / (norm1 * norm2)
    return float(similarity)


def compute_pairwise_similarities(
    embeddings: list[list[float]]
) -> np.ndarray:
    """
    Compute pairwise cosine similarities for a list of embeddings.

    Args:
        embeddings: List of embedding vectors

    Returns:
        Similarity matrix (n x n)
    """
    arr = np.array(embeddings)
    # Normalize
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1  # Avoid division by zero
    normalized = arr / norms

    # Compute similarity matrix
    similarity_matrix = np.dot(normalized, normalized.T)
    return similarity_matrix


def cluster_by_similarity(
    embeddings: list[list[float]],
    threshold: float = 0.8
) -> list[list[int]]:
    """
    Cluster items by similarity threshold.

    Args:
        embeddings: List of embedding vectors
        threshold: Similarity threshold for clustering

    Returns:
        List of clusters (each cluster is a list of indices)
    """
    n = len(embeddings)
    if n == 0:
        return []

    similarity_matrix = compute_pairwise_similarities(embeddings)

    # Simple greedy clustering
    assigned = [False] * n
    clusters = []

    for i in range(n):
        if assigned[i]:
            continue

        cluster = [i]
        assigned[i] = True

        for j in range(i + 1, n):
            if not assigned[j] and similarity_matrix[i, j] >= threshold:
                cluster.append(j)
                assigned[j] = True

        clusters.append(cluster)

    return clusters


class VectorStore:
    """Simple vector store for hypothesis embeddings."""

    def __init__(self):
        self.vectors: list[list[float]] = []
        self.metadata: list[dict] = []
        self.embedding_tool = EmbeddingTool()

    async def add_text(self, text: str, metadata: Optional[dict] = None) -> int:
        """Add a text to the store."""
        vector = await self.embedding_tool.embed_text(text)
        self.vectors.append(vector)
        self.metadata.append(metadata or {})
        return len(self.vectors) - 1

    async def add_texts(
        self,
        texts: list[str],
        metadatas: Optional[list[dict]] = None
    ) -> list[int]:
        """Add multiple texts to the store."""
        vectors = await self.embedding_tool.embed_texts(texts)
        start_idx = len(self.vectors)

        self.vectors.extend(vectors)

        if metadatas:
            self.metadata.extend(metadatas)
        else:
            self.metadata.extend([{}] * len(texts))

        return list(range(start_idx, len(self.vectors)))

    async def search(
        self,
        query: str,
        k: int = 5
    ) -> list[tuple[int, float, dict]]:
        """
        Search for similar items.

        Args:
            query: Query text
            k: Number of results

        Returns:
            List of (index, similarity, metadata) tuples
        """
        if not self.vectors:
            return []

        query_vector = await self.embedding_tool.embed_text(query)

        similarities = []
        for i, vec in enumerate(self.vectors):
            sim = compute_similarity(query_vector, vec)
            similarities.append((i, sim, self.metadata[i]))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:k]

    def get_all_similarities(self) -> np.ndarray:
        """Get pairwise similarities of all stored vectors."""
        if not self.vectors:
            return np.array([])
        return compute_pairwise_similarities(self.vectors)
