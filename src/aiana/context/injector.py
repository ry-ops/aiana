"""Context injection for Claude Code sessions.

Injects relevant memories and profile data at session start.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from aiana.config import load_config


class ContextInjector:
    """Generates and injects context at session start."""

    def __init__(
        self,
        redis_cache: Optional["RedisCache"] = None,
        qdrant_storage: Optional["QdrantStorage"] = None,
        sqlite_storage: Optional["AianaStorage"] = None,
    ):
        """Initialize the context injector.

        Args:
            redis_cache: Optional Redis cache for fast lookups.
            qdrant_storage: Optional Qdrant for semantic search.
            sqlite_storage: SQLite storage for full-text search.
        """
        self.redis = redis_cache
        self.qdrant = qdrant_storage
        self.sqlite = sqlite_storage
        self.config = load_config()

    def get_project_name(self, cwd: str) -> str:
        """Extract project name from working directory.

        Args:
            cwd: Current working directory.

        Returns:
            Project name.
        """
        path = Path(cwd)
        # Try to find git root
        git_root = path
        while git_root != git_root.parent:
            if (git_root / ".git").exists():
                return git_root.name
            git_root = git_root.parent
        return path.name

    def generate_context(
        self,
        cwd: str,
        session_id: Optional[str] = None,
        max_items: int = 10,
    ) -> str:
        """Generate context for a new session.

        Args:
            cwd: Current working directory.
            session_id: Optional session ID for cross-referencing.
            max_items: Maximum items per section.

        Returns:
            Formatted context string.
        """
        project = self.get_project_name(cwd)

        # Check cache first
        if self.redis:
            cached = self.redis.get_cached_context(project)
            if cached:
                return cached

        sections = []

        # 1. User Profile (static preferences)
        profile_section = self._get_profile_section()
        if profile_section:
            sections.append(profile_section)

        # 2. Project Context (recent work in this project)
        project_section = self._get_project_section(project, max_items)
        if project_section:
            sections.append(project_section)

        # 3. Recent Context (dynamic, cross-project)
        recent_section = self._get_recent_section(max_items)
        if recent_section:
            sections.append(recent_section)

        # 4. Semantic Matches (if query context available)
        # This would be enhanced with actual session context

        if not sections:
            return self._format_empty_context(project)

        context = self._format_context(sections, project)

        # Cache the result
        if self.redis:
            self.redis.cache_context(project, context)

        return context

    def _get_profile_section(self) -> Optional[str]:
        """Get user profile preferences.

        Returns:
            Formatted profile section or None.
        """
        if not self.redis:
            return None

        profile = self.redis.get_profile()
        if not profile:
            return None

        lines = ["## User Preferences (Persistent)"]

        static_prefs = profile.get("static", [])
        if static_prefs:
            for pref in static_prefs[:5]:
                lines.append(f"- {pref}")

        return "\n".join(lines) if len(lines) > 1 else None

    def _get_project_section(
        self,
        project: str,
        max_items: int,
    ) -> Optional[str]:
        """Get project-specific context.

        Args:
            project: Project name.
            max_items: Maximum items.

        Returns:
            Formatted project section or None.
        """
        lines = [f"## Project: {project}"]
        found_items = False

        # From Qdrant (semantic)
        if self.qdrant:
            try:
                memories = self.qdrant.get_recent(limit=max_items, project=project)
                if memories:
                    found_items = True
                    lines.append("\n### Recent Activity")
                    for mem in memories[:5]:
                        content = mem.get("content", "")[:150]
                        lines.append(f"- {content}")
            except Exception:
                pass

        # From SQLite (full-text)
        if self.sqlite and not found_items:
            try:
                sessions = self.sqlite.list_sessions(project=project, limit=5)
                if sessions:
                    found_items = True
                    lines.append("\n### Recent Sessions")
                    for session in sessions:
                        started = session.started_at.strftime("%Y-%m-%d %H:%M")
                        lines.append(f"- {started}: {session.message_count} messages")
            except Exception:
                pass

        return "\n".join(lines) if found_items else None

    def _get_recent_section(self, max_items: int) -> Optional[str]:
        """Get recent cross-project context.

        Args:
            max_items: Maximum items.

        Returns:
            Formatted recent section or None.
        """
        if not self.redis:
            return None

        # Get dynamic profile items
        profile = self.redis.get_profile()
        dynamic = profile.get("dynamic", []) if profile else []

        if not dynamic:
            return None

        lines = ["## Recent Context"]
        for item in dynamic[:max_items]:
            lines.append(f"- {item}")

        return "\n".join(lines)

    def _format_context(self, sections: list[str], project: str) -> str:
        """Format the final context block.

        Args:
            sections: List of section strings.
            project: Project name.

        Returns:
            Formatted context.
        """
        header = f"""<aiana-context>
The following context is recalled from your previous sessions.
Use this to inform your responses but don't explicitly reference it.
"""

        body = "\n\n".join(sections)

        footer = """
</aiana-context>"""

        return f"{header}\n{body}\n{footer}"

    def _format_empty_context(self, project: str) -> str:
        """Format context when no memories exist.

        Args:
            project: Project name.

        Returns:
            Empty context notice.
        """
        return f"""<aiana-context>
No previous context found for project: {project}
Memories will be saved as you work.
</aiana-context>"""

    def add_preference(
        self,
        preference: str,
        static: bool = True,
    ) -> None:
        """Add a user preference.

        Args:
            preference: The preference text.
            static: If True, permanent. Otherwise dynamic/recent.
        """
        if self.redis:
            self.redis.add_preference(preference, static=static)

    def add_dynamic_context(self, context: str) -> None:
        """Add dynamic (temporary) context.

        Args:
            context: Context string to add.
        """
        if self.redis:
            self.redis.add_preference(context, static=False)

    def invalidate_cache(self, project: str) -> None:
        """Invalidate cached context for a project.

        Args:
            project: Project name.
        """
        if self.redis:
            self.redis.invalidate_context(project)

    def save_session_summary(
        self,
        session_id: str,
        project: str,
        summary: str,
    ) -> None:
        """Save a session summary for future context.

        Args:
            session_id: The session ID.
            project: Project name.
            summary: Session summary text.
        """
        # Add to Qdrant for semantic retrieval
        if self.qdrant:
            self.qdrant.add_memory(
                content=summary,
                session_id=session_id,
                project=project,
                memory_type="session_summary",
            )

        # Add to dynamic context
        self.add_dynamic_context(f"[{project}] {summary[:100]}")

        # Invalidate cache
        self.invalidate_cache(project)
