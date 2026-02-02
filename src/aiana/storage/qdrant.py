"""Qdrant vector storage for semantic search."""

import os
import uuid
from datetime import datetime
from typing import Optional

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        PointStruct,
        VectorParams,
        Filter,
        FieldCondition,
        MatchValue,
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

from aiana.config import load_config


COLLECTION_NAME = "aiana_memories"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 embedding size


class QdrantStorage:
    """Qdrant-based vector storage for semantic search."""

    def __init__(
        self,
        url: Optional[str] = None,
        embedder: Optional["Embedder"] = None,
    ):
        """Initialize Qdrant storage.

        Args:
            url: Qdrant server URL. Defaults to QDRANT_URL env var or localhost.
            embedder: Embedder instance for text-to-vector conversion.
        """
        if not QDRANT_AVAILABLE:
            raise ImportError(
                "Qdrant client not installed. Install with: pip install qdrant-client"
            )

        self.url = url or os.environ.get("QDRANT_URL", "http://localhost:6333")
        self.client = QdrantClient(url=self.url)
        self.embedder = embedder
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Ensure the collection exists."""
        collections = self.client.get_collections().collections
        if not any(c.name == COLLECTION_NAME for c in collections):
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )

    def add_memory(
        self,
        content: str,
        session_id: str,
        project: Optional[str] = None,
        memory_type: str = "conversation",
        metadata: Optional[dict] = None,
    ) -> str:
        """Add a memory to the vector store.

        Args:
            content: The text content to store.
            session_id: Associated session ID.
            project: Project path or name.
            memory_type: Type of memory (conversation, preference, pattern).
            metadata: Additional metadata.

        Returns:
            The memory ID.
        """
        if not self.embedder:
            raise RuntimeError("Embedder required for adding memories")

        memory_id = str(uuid.uuid4())
        vector = self.embedder.embed(content)

        payload = {
            "content": content,
            "session_id": session_id,
            "project": project or "",
            "memory_type": memory_type,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {}),
        }

        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=memory_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )

        return memory_id

    def search(
        self,
        query: str,
        limit: int = 10,
        project: Optional[str] = None,
        memory_type: Optional[str] = None,
        min_score: float = 0.5,
    ) -> list[dict]:
        """Search memories semantically.

        Args:
            query: Search query text.
            limit: Maximum results to return.
            project: Filter by project.
            memory_type: Filter by memory type.
            min_score: Minimum similarity score (0-1).

        Returns:
            List of matching memories with scores.
        """
        if not self.embedder:
            raise RuntimeError("Embedder required for searching memories")

        query_vector = self.embedder.embed(query)

        # Build filter conditions
        conditions = []
        if project:
            conditions.append(
                FieldCondition(
                    key="project",
                    match=MatchValue(value=project),
                )
            )
        if memory_type:
            conditions.append(
                FieldCondition(
                    key="memory_type",
                    match=MatchValue(value=memory_type),
                )
            )

        search_filter = Filter(must=conditions) if conditions else None

        results = self.client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit,
            query_filter=search_filter,
            score_threshold=min_score,
        )

        return [
            {
                "id": str(hit.id),
                "content": hit.payload.get("content", ""),
                "score": hit.score,
                "session_id": hit.payload.get("session_id"),
                "project": hit.payload.get("project"),
                "memory_type": hit.payload.get("memory_type"),
                "timestamp": hit.payload.get("timestamp"),
                **{k: v for k, v in hit.payload.items()
                   if k not in ("content", "session_id", "project", "memory_type", "timestamp")},
            }
            for hit in results
        ]

    def get_recent(
        self,
        limit: int = 20,
        project: Optional[str] = None,
    ) -> list[dict]:
        """Get recent memories (non-semantic, by timestamp).

        Args:
            limit: Maximum results.
            project: Filter by project.

        Returns:
            List of recent memories.
        """
        # Scroll through collection sorted by timestamp
        conditions = []
        if project:
            conditions.append(
                FieldCondition(
                    key="project",
                    match=MatchValue(value=project),
                )
            )

        scroll_filter = Filter(must=conditions) if conditions else None

        results, _ = self.client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=scroll_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        # Sort by timestamp descending
        memories = [
            {
                "id": str(point.id),
                "content": point.payload.get("content", ""),
                "session_id": point.payload.get("session_id"),
                "project": point.payload.get("project"),
                "memory_type": point.payload.get("memory_type"),
                "timestamp": point.payload.get("timestamp"),
            }
            for point in results
        ]

        memories.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return memories[:limit]

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID.

        Args:
            memory_id: The memory ID to delete.

        Returns:
            True if deleted successfully.
        """
        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=[memory_id],
        )
        return True

    def delete_session(self, session_id: str) -> int:
        """Delete all memories for a session.

        Args:
            session_id: The session ID.

        Returns:
            Number of memories deleted.
        """
        # Get count before deletion
        results, _ = self.client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="session_id",
                        match=MatchValue(value=session_id),
                    )
                ]
            ),
            limit=1000,
            with_payload=False,
        )
        count = len(results)

        # Delete by filter
        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="session_id",
                        match=MatchValue(value=session_id),
                    )
                ]
            ),
        )

        return count

    def get_stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dictionary with collection stats.
        """
        info = self.client.get_collection(COLLECTION_NAME)
        return {
            "total_memories": info.points_count,
            "indexed_vectors": info.indexed_vectors_count or 0,
            "status": info.status.value,
        }

    def health_check(self) -> bool:
        """Check if Qdrant is healthy.

        Returns:
            True if healthy.
        """
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False
