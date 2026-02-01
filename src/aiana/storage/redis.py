"""Redis cache layer for Aiana."""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# Cache key prefixes
PREFIX_SESSION = "aiana:session:"
PREFIX_CONTEXT = "aiana:context:"
PREFIX_PROFILE = "aiana:profile:"
PREFIX_RECENT = "aiana:recent:"

# Default TTLs
TTL_SESSION = 3600 * 24  # 24 hours
TTL_CONTEXT = 3600 * 4   # 4 hours
TTL_PROFILE = 3600 * 24 * 7  # 7 days


class RedisCache:
    """Redis-based caching for hot data and session state."""

    def __init__(self, url: Optional[str] = None):
        """Initialize Redis connection.

        Args:
            url: Redis URL. Defaults to REDIS_URL env var or localhost.
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis client not installed. Install with: pip install redis"
            )

        self.url = url or os.environ.get("REDIS_URL", "redis://localhost:6379")
        self.client = redis.from_url(self.url, decode_responses=True)

    # =========================================================================
    # Session State
    # =========================================================================

    def set_active_session(
        self,
        session_id: str,
        project: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Mark a session as active.

        Args:
            session_id: The session ID.
            project: Project path.
            metadata: Additional session metadata.
        """
        key = f"{PREFIX_SESSION}{session_id}"
        data = {
            "session_id": session_id,
            "project": project,
            "started_at": datetime.now().isoformat(),
            "message_count": 0,
            **(metadata or {}),
        }
        self.client.setex(key, TTL_SESSION, json.dumps(data))

        # Also track in active sessions set
        self.client.sadd("aiana:active_sessions", session_id)

    def get_active_session(self, session_id: str) -> Optional[dict]:
        """Get active session data.

        Args:
            session_id: The session ID.

        Returns:
            Session data or None.
        """
        key = f"{PREFIX_SESSION}{session_id}"
        data = self.client.get(key)
        return json.loads(data) if data else None

    def update_session(self, session_id: str, updates: dict) -> None:
        """Update session data.

        Args:
            session_id: The session ID.
            updates: Fields to update.
        """
        key = f"{PREFIX_SESSION}{session_id}"
        data = self.client.get(key)
        if data:
            session = json.loads(data)
            session.update(updates)
            ttl = self.client.ttl(key)
            self.client.setex(key, max(ttl, 60), json.dumps(session))

    def end_session(self, session_id: str) -> None:
        """Mark a session as ended.

        Args:
            session_id: The session ID.
        """
        key = f"{PREFIX_SESSION}{session_id}"
        self.client.delete(key)
        self.client.srem("aiana:active_sessions", session_id)

    def get_active_sessions(self) -> list[str]:
        """Get all active session IDs.

        Returns:
            List of active session IDs.
        """
        return list(self.client.smembers("aiana:active_sessions"))

    def increment_message_count(self, session_id: str) -> int:
        """Increment message count for a session.

        Args:
            session_id: The session ID.

        Returns:
            New message count.
        """
        data = self.get_active_session(session_id)
        if data:
            count = data.get("message_count", 0) + 1
            self.update_session(session_id, {"message_count": count})
            return count
        return 0

    # =========================================================================
    # Context Cache
    # =========================================================================

    def cache_context(
        self,
        project: str,
        context: str,
        ttl: int = TTL_CONTEXT,
    ) -> None:
        """Cache generated context for a project.

        Args:
            project: Project identifier.
            context: The context string.
            ttl: Time to live in seconds.
        """
        key = f"{PREFIX_CONTEXT}{project}"
        self.client.setex(key, ttl, context)

    def get_cached_context(self, project: str) -> Optional[str]:
        """Get cached context for a project.

        Args:
            project: Project identifier.

        Returns:
            Cached context or None.
        """
        key = f"{PREFIX_CONTEXT}{project}"
        return self.client.get(key)

    def invalidate_context(self, project: str) -> None:
        """Invalidate cached context.

        Args:
            project: Project identifier.
        """
        key = f"{PREFIX_CONTEXT}{project}"
        self.client.delete(key)

    # =========================================================================
    # User Profile
    # =========================================================================

    def set_profile(self, user_id: str, profile: dict) -> None:
        """Set user profile data.

        Args:
            user_id: User identifier (usually "default" for single-user).
            profile: Profile data with static and dynamic preferences.
        """
        key = f"{PREFIX_PROFILE}{user_id}"
        self.client.setex(key, TTL_PROFILE, json.dumps(profile))

    def get_profile(self, user_id: str = "default") -> Optional[dict]:
        """Get user profile.

        Args:
            user_id: User identifier.

        Returns:
            Profile data or None.
        """
        key = f"{PREFIX_PROFILE}{user_id}"
        data = self.client.get(key)
        return json.loads(data) if data else None

    def update_profile(self, user_id: str, updates: dict) -> None:
        """Update profile with new preferences.

        Args:
            user_id: User identifier.
            updates: Fields to update.
        """
        profile = self.get_profile(user_id) or {"static": [], "dynamic": []}
        profile.update(updates)
        self.set_profile(user_id, profile)

    def add_preference(
        self,
        preference: str,
        static: bool = True,
        user_id: str = "default",
    ) -> None:
        """Add a preference to the profile.

        Args:
            preference: The preference text.
            static: If True, add to static (permanent). Otherwise dynamic.
            user_id: User identifier.
        """
        profile = self.get_profile(user_id) or {"static": [], "dynamic": []}
        key = "static" if static else "dynamic"

        if preference not in profile[key]:
            profile[key].append(preference)
            # Keep dynamic list limited
            if key == "dynamic" and len(profile[key]) > 20:
                profile[key] = profile[key][-20:]
            self.set_profile(user_id, profile)

    # =========================================================================
    # Recent Activity
    # =========================================================================

    def add_recent_activity(
        self,
        activity_type: str,
        description: str,
        project: Optional[str] = None,
        metadata: Optional[dict] = None,
        max_items: int = 100,
    ) -> None:
        """Add a recent activity entry.

        Args:
            activity_type: Type of activity (e.g., "search", "memory_add").
            description: Activity description.
            project: Associated project.
            metadata: Additional metadata.
            max_items: Maximum items to keep.
        """
        entry = {
            "type": activity_type,
            "description": description,
            "project": project,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {}),
        }

        key = f"{PREFIX_RECENT}activities"
        self.client.lpush(key, json.dumps(entry))
        self.client.ltrim(key, 0, max_items - 1)

    def get_recent_activities(
        self,
        limit: int = 20,
        activity_type: Optional[str] = None,
    ) -> list[dict]:
        """Get recent activities.

        Args:
            limit: Maximum items to return.
            activity_type: Filter by type.

        Returns:
            List of recent activities.
        """
        key = f"{PREFIX_RECENT}activities"
        items = self.client.lrange(key, 0, limit * 2)  # Fetch extra for filtering

        activities = [json.loads(item) for item in items]

        if activity_type:
            activities = [a for a in activities if a.get("type") == activity_type]

        return activities[:limit]

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def health_check(self) -> bool:
        """Check if Redis is healthy.

        Returns:
            True if healthy.
        """
        try:
            self.client.ping()
            return True
        except Exception:
            return False

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with stats.
        """
        info = self.client.info("memory")
        return {
            "used_memory": info.get("used_memory_human", "unknown"),
            "used_memory_peak": info.get("used_memory_peak_human", "unknown"),
            "active_sessions": len(self.get_active_sessions()),
            "connected": self.health_check(),
        }

    def flush_project(self, project: str) -> int:
        """Flush all cached data for a project.

        Args:
            project: Project identifier.

        Returns:
            Number of keys deleted.
        """
        pattern = f"aiana:*:{project}*"
        keys = list(self.client.scan_iter(pattern))
        if keys:
            return self.client.delete(*keys)
        return 0

    def close(self) -> None:
        """Close the Redis connection."""
        self.client.close()
