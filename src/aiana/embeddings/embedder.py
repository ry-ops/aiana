"""Text embedding using sentence-transformers."""

import os
from typing import Optional, Union

try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


# Default model - small, fast, good quality
DEFAULT_MODEL = "all-MiniLM-L6-v2"

# Singleton instance
_embedder: Optional["Embedder"] = None


class Embedder:
    """Text-to-vector embedder using sentence-transformers."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ):
        """Initialize the embedder.

        Args:
            model_name: HuggingFace model name. Defaults to all-MiniLM-L6-v2.
            device: Device to use ('cpu', 'cuda', 'mps'). Auto-detected if None.
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )

        self.model_name = model_name or os.environ.get(
            "AIANA_EMBEDDING_MODEL", DEFAULT_MODEL
        )
        self.device = device or self._detect_device()
        self.model = SentenceTransformer(self.model_name, device=self.device)
        self._dimension = self.model.get_sentence_embedding_dimension()

    def _detect_device(self) -> str:
        """Detect the best available device.

        Returns:
            Device string ('cuda', 'mps', or 'cpu').
        """
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    @property
    def dimension(self) -> int:
        """Get the embedding dimension.

        Returns:
            Vector dimension size.
        """
        return self._dimension

    def embed(self, text: Union[str, list[str]]) -> Union[list[float], list[list[float]]]:
        """Embed text into vectors.

        Args:
            text: Single text or list of texts to embed.

        Returns:
            Vector(s) as list of floats.
        """
        single = isinstance(text, str)
        texts = [text] if single else text

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        # Convert to list for JSON serialization
        if single:
            return embeddings[0].tolist()
        return [e.tolist() for e in embeddings]

    def embed_with_metadata(
        self,
        text: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Embed text and return with metadata.

        Args:
            text: Text to embed.
            metadata: Additional metadata to include.

        Returns:
            Dictionary with vector and metadata.
        """
        vector = self.embed(text)
        return {
            "vector": vector,
            "text": text,
            "model": self.model_name,
            "dimension": self._dimension,
            **(metadata or {}),
        }

    def similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts.

        Args:
            text1: First text.
            text2: Second text.

        Returns:
            Similarity score (0-1).
        """
        vectors = self.embed([text1, text2])
        # Dot product of normalized vectors = cosine similarity
        return sum(a * b for a, b in zip(vectors[0], vectors[1]))

    def batch_embed(
        self,
        texts: list[str],
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> list[list[float]]:
        """Embed a batch of texts efficiently.

        Args:
            texts: List of texts to embed.
            batch_size: Batch size for processing.
            show_progress: Show progress bar.

        Returns:
            List of vectors.
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=show_progress,
        )

        return [e.tolist() for e in embeddings]


def get_embedder(
    model_name: Optional[str] = None,
    force_new: bool = False,
) -> Embedder:
    """Get or create a singleton embedder instance.

    Args:
        model_name: Model to use. If different from current, creates new.
        force_new: Force creation of new instance.

    Returns:
        Embedder instance.
    """
    global _embedder

    if force_new or _embedder is None:
        _embedder = Embedder(model_name=model_name)
    elif model_name and _embedder.model_name != model_name:
        _embedder = Embedder(model_name=model_name)

    return _embedder
