"""Storage backends for Aiana."""

from aiana.storage.sqlite import AianaStorage

# Optional backends
try:
    from aiana.storage.redis import RedisCache
except ImportError:
    RedisCache = None

try:
    from aiana.storage.qdrant import QdrantStorage
except ImportError:
    QdrantStorage = None

try:
    from aiana.storage.mem0 import Mem0Storage
except ImportError:
    Mem0Storage = None

__all__ = ["AianaStorage", "RedisCache", "QdrantStorage", "Mem0Storage"]
