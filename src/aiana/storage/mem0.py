"""Mem0 memory storage for enhanced AI memory management."""

import os
from datetime import datetime
from typing import Optional

try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False


class Mem0Storage:
    """Mem0-based memory storage with automatic consolidation and deduplication.

    Mem0 provides enhanced memory management features:
    - Automatic memory extraction from conversations
    - Memory consolidation and deduplication
    - User/agent memory separation
    - Built-in relevance scoring

    Uses existing Qdrant instance as the vector store backend.
    """

    def __init__(
        self,
        qdrant_url: Optional[str] = None,
        qdrant_collection: str = "aiana_mem0",
        user_id: str = "default",
    ):
        """Initialize Mem0 storage.

        Args:
            qdrant_url: Qdrant server URL. Defaults to QDRANT_URL env var or localhost.
            qdrant_collection: Collection name for Mem0 memories.
            user_id: Default user ID for memory operations.
        """
        if not MEM0_AVAILABLE:
            raise ImportError(
                "Mem0 not installed. Install with: pip install mem0ai"
            )

        self.qdrant_url = qdrant_url or os.environ.get("QDRANT_URL", "http://localhost:6333")
        self.collection_name = qdrant_collection
        self.default_user_id = user_id

        # Parse Qdrant URL for host and port
        url_parts = self.qdrant_url.replace("http://", "").replace("https://", "").split(":")
        qdrant_host = url_parts[0]
        qdrant_port = int(url_parts[1]) if len(url_parts) > 1 else 6333

        # Configure Mem0 with Qdrant backend
        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": self.collection_name,
                    "host": qdrant_host,
                    "port": qdrant_port,
                    "embedding_model_dims": 384,
                }
            },
            "embedder": {
                "provider": "huggingface",
                "config": {
                    "model": "all-MiniLM-L6-v2",
                }
            },
            "version": "v1.1",
        }

        self.memory = Memory.from_config(config)

    def add_memory(
        self,
        content: str,
        session_id: str,
        project: Optional[str] = None,
        memory_type: str = "conversation",
        metadata: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Add a memory using Mem0's intelligent memory system.

        Mem0 automatically:
        - Extracts key information from content
        - Deduplicates against existing memories
        - Consolidates related memories

        Args:
            content: The text content to store.
            session_id: Associated session ID.
            project: Project path or name.
            memory_type: Type of memory (conversation, preference, pattern, insight).
            metadata: Additional metadata.
            user_id: User ID for memory. Defaults to instance default.

        Returns:
            The memory ID (or first memory ID if multiple created).
        """
        effective_user_id = user_id or self.default_user_id

        # Build metadata for Mem0
        mem0_metadata = {
            "session_id": session_id,
            "project": project or "",
            "memory_type": memory_type,
            "timestamp": datetime.now().isoformat(),
            "source": "aiana",
            **(metadata or {}),
        }

        # Use Mem0's add method - it automatically handles extraction and dedup
        result = self.memory.add(
            content,
            user_id=effective_user_id,
            metadata=mem0_metadata,
        )

        # Mem0 returns a dict with 'results' containing list of memory operations
        if result and "results" in result and len(result["results"]) > 0:
            return result["results"][0].get("id", "")

        # Fallback for different response formats
        if result and "id" in result:
            return result["id"]

        return ""

    def search(
        self,
        query: str,
        limit: int = 10,
        project: Optional[str] = None,
        memory_type: Optional[str] = None,
        min_score: float = 0.5,
        user_id: Optional[str] = None,
    ) -> list[dict]:
        """Search memories using Mem0's semantic search.

        Args:
            query: Search query text.
            limit: Maximum results to return.
            project: Filter by project.
            memory_type: Filter by memory type.
            min_score: Minimum similarity score (0-1).
            user_id: User ID to search for.

        Returns:
            List of matching memories with scores.
        """
        effective_user_id = user_id or self.default_user_id

        # Use Mem0's search
        results = self.memory.search(
            query,
            user_id=effective_user_id,
            limit=limit * 2,  # Get extra to filter
        )

        # Transform results to match QdrantStorage interface
        memories = []
        for item in results.get("results", results) if isinstance(results, dict) else results:
            # Handle different result formats
            if isinstance(item, dict):
                memory_data = item.get("memory", item)
                score = item.get("score", 1.0)
                metadata = item.get("metadata", {})
            else:
                memory_data = str(item)
                score = 1.0
                metadata = {}

            # Skip if below minimum score
            if score < min_score:
                continue

            # Apply project filter if specified
            item_project = metadata.get("project", "")
            if project and item_project != project:
                continue

            # Apply memory_type filter if specified
            item_type = metadata.get("memory_type", "")
            if memory_type and item_type != memory_type:
                continue

            memories.append({
                "id": item.get("id", "") if isinstance(item, dict) else "",
                "content": memory_data if isinstance(memory_data, str) else memory_data.get("content", str(memory_data)),
                "score": score,
                "session_id": metadata.get("session_id"),
                "project": item_project,
                "memory_type": item_type,
                "timestamp": metadata.get("timestamp"),
                **{k: v for k, v in metadata.items()
                   if k not in ("session_id", "project", "memory_type", "timestamp")},
            })

            if len(memories) >= limit:
                break

        return memories

    def get_all(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get all memories for a user.

        Args:
            user_id: User ID to get memories for.
            limit: Maximum memories to return.

        Returns:
            List of all memories.
        """
        effective_user_id = user_id or self.default_user_id

        results = self.memory.get_all(user_id=effective_user_id)

        memories = []
        for item in results.get("results", results) if isinstance(results, dict) else results:
            if isinstance(item, dict):
                metadata = item.get("metadata", {})
                memories.append({
                    "id": item.get("id", ""),
                    "content": item.get("memory", ""),
                    "session_id": metadata.get("session_id"),
                    "project": metadata.get("project"),
                    "memory_type": metadata.get("memory_type"),
                    "timestamp": metadata.get("timestamp"),
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                })

            if len(memories) >= limit:
                break

        return memories

    def get_recent(
        self,
        limit: int = 20,
        project: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> list[dict]:
        """Get recent memories.

        Args:
            limit: Maximum results.
            project: Filter by project.
            user_id: User ID to get memories for.

        Returns:
            List of recent memories sorted by timestamp.
        """
        all_memories = self.get_all(user_id=user_id, limit=limit * 2)

        # Filter by project if specified
        if project:
            all_memories = [m for m in all_memories if m.get("project") == project]

        # Sort by timestamp descending
        all_memories.sort(
            key=lambda x: x.get("timestamp") or x.get("updated_at") or "",
            reverse=True
        )

        return all_memories[:limit]

    def update_memory(
        self,
        memory_id: str,
        content: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Update an existing memory.

        Args:
            memory_id: The memory ID to update.
            content: New content for the memory.
            user_id: User ID for the memory.

        Returns:
            True if updated successfully.
        """
        try:
            self.memory.update(memory_id, content)
            return True
        except Exception:
            return False

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID.

        Args:
            memory_id: The memory ID to delete.

        Returns:
            True if deleted successfully.
        """
        try:
            self.memory.delete(memory_id)
            return True
        except Exception:
            return False

    def delete_session(self, session_id: str, user_id: Optional[str] = None) -> int:
        """Delete all memories for a session.

        Args:
            session_id: The session ID.
            user_id: User ID to search in.

        Returns:
            Number of memories deleted.
        """
        all_memories = self.get_all(user_id=user_id)

        deleted = 0
        for memory in all_memories:
            if memory.get("session_id") == session_id:
                if self.delete_memory(memory["id"]):
                    deleted += 1

        return deleted

    def delete_all(self, user_id: Optional[str] = None) -> int:
        """Delete all memories for a user.

        Args:
            user_id: User ID to delete memories for.

        Returns:
            Number of memories deleted.
        """
        effective_user_id = user_id or self.default_user_id

        try:
            self.memory.delete_all(user_id=effective_user_id)
            return -1  # Mem0 doesn't return count
        except Exception:
            return 0

    def add_conversation(
        self,
        messages: list[dict],
        session_id: str,
        project: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> list[str]:
        """Add memories from a conversation (Mem0's specialty).

        Mem0 automatically extracts and stores relevant information
        from the conversation.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            session_id: Associated session ID.
            project: Project path or name.
            user_id: User ID for memories.

        Returns:
            List of memory IDs created.
        """
        effective_user_id = user_id or self.default_user_id

        metadata = {
            "session_id": session_id,
            "project": project or "",
            "memory_type": "conversation",
            "timestamp": datetime.now().isoformat(),
            "source": "aiana",
        }

        # Use Mem0's conversation memory extraction
        result = self.memory.add(
            messages,
            user_id=effective_user_id,
            metadata=metadata,
        )

        # Extract IDs from result
        ids = []
        if result and "results" in result:
            for item in result["results"]:
                if "id" in item:
                    ids.append(item["id"])

        return ids

    def get_stats(self) -> dict:
        """Get storage statistics.

        Returns:
            Dictionary with memory stats.
        """
        all_memories = self.get_all()

        # Count by type
        type_counts = {}
        project_counts = {}
        for memory in all_memories:
            mtype = memory.get("memory_type", "unknown")
            type_counts[mtype] = type_counts.get(mtype, 0) + 1

            proj = memory.get("project", "unknown")
            project_counts[proj] = project_counts.get(proj, 0) + 1

        return {
            "total_memories": len(all_memories),
            "by_type": type_counts,
            "by_project": project_counts,
            "backend": "mem0",
            "collection": self.collection_name,
        }

    def health_check(self) -> bool:
        """Check if Mem0 and Qdrant are healthy.

        Returns:
            True if healthy.
        """
        try:
            # Try a simple operation to verify connectivity
            self.memory.get_all(user_id=self.default_user_id, limit=1)
            return True
        except Exception:
            return False
