"""MCP Server for Aiana - exposes memory operations to Claude."""

import asyncio
import json
from typing import Optional

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from aiana.config import load_config
from aiana.storage import AianaStorage


class AianaMCPServer:
    """MCP Server exposing Aiana memory operations."""

    def __init__(self):
        """Initialize the MCP server."""
        if not MCP_AVAILABLE:
            raise ImportError(
                "MCP SDK not installed. Install with: pip install mcp"
            )

        self.config = load_config()
        self.server = Server("aiana")
        self.sqlite = None
        self.redis = None
        self.qdrant = None
        self.mem0 = None  # Mem0 storage (primary)
        self.embedder = None
        self.injector = None

        self._setup_handlers()

    def _init_backends(self) -> None:
        """Initialize storage backends (lazy loading)."""
        if self.sqlite is None:
            self.sqlite = AianaStorage()

        # Try to initialize optional backends
        try:
            from aiana.storage.redis import RedisCache
            self.redis = RedisCache()
        except Exception:
            pass

        # Try Mem0 first (primary vector store)
        try:
            from aiana.storage.mem0 import Mem0Storage
            self.mem0 = Mem0Storage()
        except Exception:
            pass

        # Fall back to direct Qdrant if Mem0 unavailable
        if self.mem0 is None:
            try:
                from aiana.embeddings import get_embedder
                from aiana.storage.qdrant import QdrantStorage
                self.embedder = get_embedder()
                self.qdrant = QdrantStorage(embedder=self.embedder)
            except Exception:
                pass

        try:
            from aiana.context import ContextInjector
            self.injector = ContextInjector(
                redis_cache=self.redis,
                qdrant_storage=self.qdrant,
                mem0_storage=self.mem0,
                sqlite_storage=self.sqlite,
            )
        except Exception:
            pass

    def _setup_handlers(self) -> None:
        """Set up MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available Aiana tools."""
            return [
                Tool(
                    name="memory_search",
                    description="Search through past conversations and memories semantically",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query",
                            },
                            "project": {
                                "type": "string",
                                "description": "Filter by project name (optional)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results (default 10)",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="memory_add",
                    description="Save a memory or note for future recall",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The memory content to save",
                            },
                            "memory_type": {
                                "type": "string",
                                "enum": ["note", "preference", "pattern", "insight"],
                                "description": "Type of memory",
                                "default": "note",
                            },
                            "project": {
                                "type": "string",
                                "description": "Associated project (optional)",
                            },
                        },
                        "required": ["content"],
                    },
                ),
                Tool(
                    name="memory_recall",
                    description="Recall context for the current project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {
                                "type": "string",
                                "description": "Project to recall context for",
                            },
                            "max_items": {
                                "type": "integer",
                                "description": "Maximum items per section",
                                "default": 5,
                            },
                        },
                        "required": ["project"],
                    },
                ),
                Tool(
                    name="session_list",
                    description="List recorded conversation sessions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {
                                "type": "string",
                                "description": "Filter by project (optional)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum sessions (default 20)",
                                "default": 20,
                            },
                        },
                    },
                ),
                Tool(
                    name="session_show",
                    description="Show details of a specific session",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID (can be partial)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum messages to show",
                            },
                        },
                        "required": ["session_id"],
                    },
                ),
                Tool(
                    name="preference_add",
                    description="Add a user preference for future context",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "preference": {
                                "type": "string",
                                "description": "The preference to save",
                            },
                            "permanent": {
                                "type": "boolean",
                                "description": "If true, preference persists long-term",
                                "default": True,
                            },
                        },
                        "required": ["preference"],
                    },
                ),
                Tool(
                    name="aiana_status",
                    description="Get Aiana system status and statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="memory_feedback",
                    description="Provide feedback on recalled memories to improve future retrieval. Call this after using memory_search or memory_recall to rate how helpful the results were.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "memory_id": {
                                "type": "string",
                                "description": "ID of the memory being rated (from search results)",
                            },
                            "memory_source": {
                                "type": "string",
                                "enum": ["semantic", "fulltext", "recall"],
                                "description": "Source of the memory (semantic=Qdrant, fulltext=SQLite FTS, recall=context injection)",
                            },
                            "query": {
                                "type": "string",
                                "description": "The original query that returned this memory",
                            },
                            "rating": {
                                "type": "integer",
                                "enum": [1, 0, -1],
                                "description": "1=helpful (answered the question), 0=not helpful (irrelevant), -1=harmful (wrong/misleading)",
                            },
                            "reason": {
                                "type": "string",
                                "description": "Brief explanation of the rating (optional but helpful for improving retrieval)",
                            },
                        },
                        "required": ["memory_id", "memory_source", "query", "rating"],
                    },
                ),
                Tool(
                    name="feedback_summary",
                    description="Get a summary of memory feedback to understand recall quality and patterns",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool calls."""
            self._init_backends()

            try:
                if name == "memory_search":
                    result = await self._memory_search(
                        query=arguments["query"],
                        project=arguments.get("project"),
                        limit=arguments.get("limit", 10),
                    )
                elif name == "memory_add":
                    result = await self._memory_add(
                        content=arguments["content"],
                        memory_type=arguments.get("memory_type", "note"),
                        project=arguments.get("project"),
                    )
                elif name == "memory_recall":
                    result = await self._memory_recall(
                        project=arguments["project"],
                        max_items=arguments.get("max_items", 5),
                    )
                elif name == "session_list":
                    result = await self._session_list(
                        project=arguments.get("project"),
                        limit=arguments.get("limit", 20),
                    )
                elif name == "session_show":
                    result = await self._session_show(
                        session_id=arguments["session_id"],
                        limit=arguments.get("limit"),
                    )
                elif name == "preference_add":
                    result = await self._preference_add(
                        preference=arguments["preference"],
                        permanent=arguments.get("permanent", True),
                    )
                elif name == "aiana_status":
                    result = await self._status()
                elif name == "memory_feedback":
                    result = await self._memory_feedback(
                        memory_id=arguments["memory_id"],
                        memory_source=arguments["memory_source"],
                        query=arguments["query"],
                        rating=arguments["rating"],
                        reason=arguments.get("reason"),
                    )
                elif name == "feedback_summary":
                    result = await self._feedback_summary()
                else:
                    result = {"error": f"Unknown tool: {name}"}

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}),
                )]

    async def _memory_search(
        self,
        query: str,
        project: Optional[str] = None,
        limit: int = 10,
    ) -> dict:
        """Search memories semantically."""
        results = []

        # Try Mem0 first (primary semantic search with enhanced memory)
        if self.mem0:
            try:
                mem0_results = self.mem0.search(
                    query=query,
                    project=project,
                    limit=limit,
                )
                results.extend([
                    {
                        "source": "mem0",
                        "id": r.get("id", ""),
                        "score": r.get("score", 1.0),
                        "content": r["content"],
                        "project": r.get("project"),
                        "timestamp": r.get("timestamp"),
                    }
                    for r in mem0_results
                ])
            except Exception:
                pass

        # Fall back to direct Qdrant if Mem0 unavailable or returned few results
        if self.qdrant and len(results) < limit:
            try:
                qdrant_results = self.qdrant.search(
                    query=query,
                    project=project,
                    limit=limit - len(results),
                )
                results.extend([
                    {
                        "source": "semantic",
                        "id": r.get("id", ""),
                        "score": r["score"],
                        "content": r["content"],
                        "project": r.get("project"),
                        "timestamp": r.get("timestamp"),
                    }
                    for r in qdrant_results
                ])
            except Exception:
                pass

        # Fallback to SQLite FTS
        if self.sqlite and len(results) < limit:
            try:
                messages = self.sqlite.search(
                    query=query,
                    project=project,
                    limit=limit - len(results),
                )
                results.extend([
                    {
                        "source": "fulltext",
                        "content": m.content[:500],
                        "session_id": m.session_id,
                        "timestamp": m.timestamp.isoformat(),
                    }
                    for m in messages
                ])
            except Exception:
                pass

        return {
            "query": query,
            "project": project,
            "count": len(results),
            "results": results,
        }

    async def _memory_add(
        self,
        content: str,
        memory_type: str = "note",
        project: Optional[str] = None,
    ) -> dict:
        """Add a memory."""
        memory_id = None
        backend = None

        # Try Mem0 first (with automatic memory extraction and deduplication)
        if self.mem0:
            try:
                memory_id = self.mem0.add_memory(
                    content=content,
                    session_id="manual",
                    project=project,
                    memory_type=memory_type,
                )
                backend = "mem0"
            except Exception:
                pass

        # Fall back to direct Qdrant
        if memory_id is None and self.qdrant:
            memory_id = self.qdrant.add_memory(
                content=content,
                session_id="manual",
                project=project,
                memory_type=memory_type,
            )
            backend = "qdrant"

        return {
            "status": "saved",
            "memory_id": memory_id,
            "content": content[:100] + "..." if len(content) > 100 else content,
            "type": memory_type,
            "project": project,
            "backend": backend,
        }

    async def _memory_recall(
        self,
        project: str,
        max_items: int = 5,
    ) -> dict:
        """Recall context for a project."""
        if self.injector:
            context = self.injector.generate_context(
                cwd=f"/projects/{project}",  # Simulated path
                max_items=max_items,
            )
            return {
                "project": project,
                "context": context,
            }

        return {
            "project": project,
            "context": f"No context available for {project}",
        }

    async def _session_list(
        self,
        project: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        """List sessions."""
        if not self.sqlite:
            return {"error": "SQLite storage not available"}

        sessions = self.sqlite.list_sessions(project=project, limit=limit)

        return {
            "count": len(sessions),
            "sessions": [
                {
                    "id": s.id[:8],
                    "project": s.project_path,
                    "started": s.started_at.isoformat(),
                    "messages": s.message_count,
                    "tokens": s.token_count,
                    "active": s.is_active,
                }
                for s in sessions
            ],
        }

    async def _session_show(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> dict:
        """Show session details."""
        if not self.sqlite:
            return {"error": "SQLite storage not available"}

        # Find session by prefix
        sessions = self.sqlite.list_sessions(limit=100)
        session = None
        for s in sessions:
            if s.id.startswith(session_id):
                session = s
                break

        if not session:
            return {"error": f"Session not found: {session_id}"}

        messages = self.sqlite.get_messages(session.id, limit=limit)

        return {
            "session": {
                "id": session.id,
                "project": session.project_path,
                "started": session.started_at.isoformat(),
                "ended": session.ended_at.isoformat() if session.ended_at else None,
                "messages": session.message_count,
                "tokens": session.token_count,
            },
            "messages": [
                {
                    "type": m.type.value,
                    "role": m.role,
                    "content": m.content[:500] if m.content else None,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in messages[:20]  # Limit output
            ],
        }

    async def _preference_add(
        self,
        preference: str,
        permanent: bool = True,
    ) -> dict:
        """Add a user preference."""
        if self.injector:
            self.injector.add_preference(preference, static=permanent)
            return {
                "status": "saved",
                "preference": preference,
                "permanent": permanent,
            }

        return {"error": "Context injector not available"}

    async def _status(self) -> dict:
        """Get system status."""
        status = {
            "aiana": "running",
            "backends": {},
        }

        # SQLite status
        if self.sqlite:
            try:
                stats = self.sqlite.get_stats()
                status["backends"]["sqlite"] = {
                    "status": "connected",
                    **stats,
                }
            except Exception as e:
                status["backends"]["sqlite"] = {"status": "error", "error": str(e)}

        # Redis status
        if self.redis:
            try:
                stats = self.redis.get_stats()
                status["backends"]["redis"] = {
                    "status": "connected" if stats.get("connected") else "disconnected",
                    **stats,
                }
            except Exception as e:
                status["backends"]["redis"] = {"status": "error", "error": str(e)}
        else:
            status["backends"]["redis"] = {"status": "not configured"}

        # Mem0 status (primary vector store)
        if self.mem0:
            try:
                stats = self.mem0.get_stats()
                status["backends"]["mem0"] = {
                    "status": "connected",
                    "primary": True,
                    **stats,
                }
            except Exception as e:
                status["backends"]["mem0"] = {"status": "error", "error": str(e)}
        else:
            status["backends"]["mem0"] = {"status": "not configured"}

        # Qdrant status (fallback or direct)
        if self.qdrant:
            try:
                stats = self.qdrant.get_stats()
                status["backends"]["qdrant"] = {
                    "status": "connected",
                    "primary": self.mem0 is None,  # Primary only if Mem0 not available
                    **stats,
                }
            except Exception as e:
                status["backends"]["qdrant"] = {"status": "error", "error": str(e)}
        elif self.mem0 is None:
            status["backends"]["qdrant"] = {"status": "not configured"}

        return status

    async def _memory_feedback(
        self,
        memory_id: str,
        memory_source: str,
        query: str,
        rating: int,
        reason: Optional[str] = None,
    ) -> dict:
        """Record feedback for a recalled memory."""
        if not self.sqlite:
            return {"error": "SQLite storage not available"}

        feedback_id = self.sqlite.add_feedback(
            memory_id=memory_id,
            memory_source=memory_source,
            query=query,
            rating=rating,
            reason=reason,
        )

        rating_label = {1: "helpful", 0: "not helpful", -1: "harmful"}[rating]

        return {
            "status": "recorded",
            "feedback_id": feedback_id,
            "memory_id": memory_id,
            "rating": rating_label,
            "message": "Thank you! Feedback recorded. This helps improve future memory retrieval.",
        }

    async def _feedback_summary(self) -> dict:
        """Get summary of memory feedback."""
        if not self.sqlite:
            return {"error": "SQLite storage not available"}

        return self.sqlite.get_feedback_summary()

    async def run(self) -> None:
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def main():
    """Entry point for MCP server."""
    server = AianaMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
