# SPDX-License-Identifier: Apache-2.0
"""Text encoder for language-conditioned VLA policies.

Provides instruction embeddings with zero external dependencies (TF-IDF fallback)
or optionally using sentence-transformers for higher quality embeddings.
"""

from __future__ import annotations

import hashlib
import math

import numpy as np


class TextEncoder:
    """Encode text instructions into fixed-dimensional vectors.

    Methods:
        - "tfidf": Zero-dependency TF-IDF-like bag-of-words encoding.
          Fast, deterministic, no downloads. Suitable for low-dimensional
          conditioning signals in simple VLA models.
        - "sentence_transformers": Uses sentence-transformers library for
          high-quality semantic embeddings. Requires optional dependency.
    """

    def __init__(self, method: str = "tfidf", dim: int = 64) -> None:
        if method not in ("tfidf", "sentence_transformers"):
            raise ValueError(
                f"Unknown method '{method}'. Choose from: 'tfidf', 'sentence_transformers'"
            )
        self._method = method
        self._dim = dim
        self._st_model = None

        if method == "sentence_transformers":
            self._init_sentence_transformers()

    @property
    def method(self) -> str:
        return self._method

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, text: str) -> np.ndarray:
        """Encode text into a fixed-size float32 vector.

        Args:
            text: The instruction text to encode.

        Returns:
            numpy array of shape (dim,) with dtype float32.
        """
        if self._method == "tfidf":
            return self._encode_tfidf(text)
        else:
            return self._encode_sentence_transformers(text)

    def _encode_tfidf(self, text: str) -> np.ndarray:
        """Deterministic hash-based bag-of-words encoding."""
        tokens = text.lower().split()
        vec = np.zeros(self._dim, dtype=np.float32)

        if not tokens:
            return vec

        for token in tokens:
            h = hashlib.md5(token.encode()).hexdigest()  # noqa: S324
            idx = int(h[:8], 16) % self._dim
            sign = 1.0 if int(h[8:16], 16) % 2 == 0 else -1.0
            idf = 1.0 / math.log(2.0 + len(token))
            vec[idx] += sign * idf

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm

        return vec

    def _init_sentence_transformers(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers is required for method='sentence_transformers'. "
                "Install with: pip install sentence-transformers"
            ) from e

        self._st_model = SentenceTransformer("all-MiniLM-L6-v2")

    def _encode_sentence_transformers(self, text: str) -> np.ndarray:
        if self._st_model is None:
            raise RuntimeError("Sentence transformer model not initialized.")

        embedding = self._st_model.encode(text, convert_to_numpy=True)
        embedding = embedding.astype(np.float32)

        if embedding.shape[0] != self._dim:
            if embedding.shape[0] > self._dim:
                embedding = embedding[: self._dim]
            else:
                padded = np.zeros(self._dim, dtype=np.float32)
                padded[: embedding.shape[0]] = embedding
                embedding = padded

        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding /= norm

        return embedding
