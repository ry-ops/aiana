"""MLX-native embedder backend (optional, torch-free).

Mirrors the :class:`~aiana.embeddings.embedder.Embedder` interface but runs on
MLX via ``mlx-embeddings``, so aiana can embed on Apple silicon without pulling
in PyTorch. Defaults to ``all-MiniLM-L6-v2`` (384-dim) to stay compatible with
the existing 384-dim ``aiana_memories`` collection and any vectors already
written by the sentence-transformers backend.

Enable with::

    pip install "aiana[mlx]"
    export AIANA_EMBEDDER_BACKEND=mlx
"""

import os
from typing import Optional, Union

try:
    import mlx.core as mx
    from mlx_embeddings import generate, load

    MLX_EMBEDDINGS_AVAILABLE = True
except ImportError:
    MLX_EMBEDDINGS_AVAILABLE = False

# Same model family as the sentence-transformers default, so embeddings live in
# the same 384-dim vector space (existing memories remain searchable).
DEFAULT_MLX_MODEL = "mlx-community/all-MiniLM-L6-v2-bf16"


class MLXEmbedder:
    """Text-to-vector embedder backed by MLX (no PyTorch)."""

    def __init__(self, model_name: Optional[str] = None):
        if not MLX_EMBEDDINGS_AVAILABLE:
            raise ImportError(
                "mlx-embeddings not installed. Install with: pip install 'aiana[mlx]'"
            )
        self.model_name = model_name or os.environ.get(
            "AIANA_EMBEDDING_MODEL", DEFAULT_MLX_MODEL
        )
        self.model, self.tokenizer = load(self.model_name)
        probe = generate(self.model, self.tokenizer, texts=["probe"])
        self._dimension = int(probe.text_embeds.shape[-1])

    @property
    def dimension(self) -> int:
        """Embedding vector dimension."""
        return self._dimension

    def embed(
        self, text: Union[str, list[str]]
    ) -> Union[list[float], list[list[float]]]:
        """Embed text into L2-normalized vectors (dot product == cosine)."""
        single = isinstance(text, str)
        texts = [text] if single else list(text)

        out = generate(self.model, self.tokenizer, texts=texts)
        embeddings = out.text_embeds
        norms = mx.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / mx.maximum(norms, 1e-12)
        mx.eval(embeddings)

        vectors = embeddings.tolist()
        return vectors[0] if single else vectors

    def similarity(self, text1: str, text2: str) -> float:
        """Cosine similarity between two texts."""
        v1, v2 = self.embed([text1, text2])
        return float(sum(a * b for a, b in zip(v1, v2)))
