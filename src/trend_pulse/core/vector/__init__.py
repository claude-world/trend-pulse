"""Vector store abstraction — pure Python TF-IDF default, extensible backend."""

from .base import VectorStore
from .simple import SimpleVectorStore

__all__ = ["VectorStore", "SimpleVectorStore"]
