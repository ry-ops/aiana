"""SQLite storage layer for Aiana."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from aiana.config import AianaConfig, load_config
from aiana.models import Message, MessageType, Session


class AianaStorage:
    """SQLite-based storage for conversation data."""

    def __init__(self, config: Optional[AianaConfig] = None):
        """Initialize storage with configuration."""
        self.config = config or load_config()
        self.db_path = self.config.storage.resolved_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    project_path TEXT NOT NULL,
                    transcript_path TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    ended_at TIMESTAMP,
                    summary TEXT,
                    message_count INTEGER DEFAULT 0,
                    token_count INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    role TEXT,
                    content TEXT,
                    tool_name TEXT,
                    tool_input TEXT,
                    parent_id TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    tokens INTEGER,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id);
                CREATE INDEX IF NOT EXISTS idx_messages_type
                    ON messages(type);
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp
                    ON messages(timestamp);
                CREATE INDEX IF NOT EXISTS idx_sessions_project
                    ON sessions(project_path);
                CREATE INDEX IF NOT EXISTS idx_sessions_started
                    ON sessions(started_at DESC);

                -- Full-text search table
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    content,
                    content=messages,
                    content_rowid=rowid
                );

                -- Triggers to keep FTS in sync
                CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
                    INSERT INTO messages_fts(rowid, content)
                    VALUES (new.rowid, new.content);
                END;

                CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
                    INSERT INTO messages_fts(messages_fts, rowid, content)
                    VALUES('delete', old.rowid, old.content);
                END;

                CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
                    INSERT INTO messages_fts(messages_fts, rowid, content)
                    VALUES('delete', old.rowid, old.content);
                    INSERT INTO messages_fts(rowid, content)
                    VALUES (new.rowid, new.content);
                END;
            """)

    def create_session(self, session: Session) -> None:
        """Create a new session."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions
                (id, project_path, transcript_path, started_at, ended_at,
                 summary, message_count, token_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.project_path,
                    session.transcript_path,
                    session.started_at.isoformat(),
                    session.ended_at.isoformat() if session.ended_at else None,
                    session.summary,
                    session.message_count,
                    session.token_count,
                    json.dumps(session.metadata),
                ),
            )

    def update_session(self, session: Session) -> None:
        """Update an existing session."""
        self.create_session(session)  # Uses INSERT OR REPLACE

    def end_session(self, session_id: str, summary: Optional[str] = None) -> None:
        """Mark a session as ended."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET ended_at = ?, summary = ?
                WHERE id = ?
                """,
                (datetime.now().isoformat(), summary, session_id),
            )

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()

            if row:
                return self._row_to_session(row)
            return None

    def list_sessions(
        self,
        project: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Session]:
        """List sessions with optional filtering."""
        with self._get_connection() as conn:
            if project:
                rows = conn.execute(
                    """
                    SELECT * FROM sessions
                    WHERE project_path LIKE ?
                    ORDER BY started_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (f"%{project}%", limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM sessions
                    ORDER BY started_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()

            return [self._row_to_session(row) for row in rows]

    def append_message(self, message: Message) -> None:
        """Append a message to storage."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO messages
                (id, session_id, type, role, content, tool_name, tool_input,
                 parent_id, timestamp, tokens, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    message.session_id,
                    message.type.value,
                    message.role,
                    message.content,
                    message.tool_name,
                    json.dumps(message.tool_input) if message.tool_input else None,
                    message.parent_id,
                    message.timestamp.isoformat(),
                    message.tokens,
                    json.dumps(message.metadata),
                ),
            )

            # Update session counts
            conn.execute(
                """
                UPDATE sessions
                SET message_count = message_count + 1,
                    token_count = token_count + COALESCE(?, 0)
                WHERE id = ?
                """,
                (message.tokens, message.session_id),
            )

    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[Message]:
        """Get messages for a session."""
        with self._get_connection() as conn:
            if limit:
                rows = conn.execute(
                    """
                    SELECT * FROM messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                    LIMIT ? OFFSET ?
                    """,
                    (session_id, limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                    """,
                    (session_id,),
                ).fetchall()

            return [self._row_to_message(row) for row in rows]

    def search(
        self,
        query: str,
        project: Optional[str] = None,
        limit: int = 50,
    ) -> list[Message]:
        """Search messages using full-text search."""
        with self._get_connection() as conn:
            if project:
                rows = conn.execute(
                    """
                    SELECT m.* FROM messages m
                    JOIN messages_fts fts ON m.rowid = fts.rowid
                    JOIN sessions s ON m.session_id = s.id
                    WHERE messages_fts MATCH ?
                    AND s.project_path LIKE ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (query, f"%{project}%", limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT m.* FROM messages m
                    JOIN messages_fts fts ON m.rowid = fts.rowid
                    WHERE messages_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (query, limit),
                ).fetchall()

            return [self._row_to_message(row) for row in rows]

    def delete_session(self, session_id: str) -> None:
        """Delete a session and its messages."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    def get_stats(self) -> dict:
        """Get storage statistics."""
        with self._get_connection() as conn:
            session_count = conn.execute(
                "SELECT COUNT(*) FROM sessions"
            ).fetchone()[0]
            message_count = conn.execute(
                "SELECT COUNT(*) FROM messages"
            ).fetchone()[0]
            total_tokens = conn.execute(
                "SELECT SUM(token_count) FROM sessions"
            ).fetchone()[0] or 0

            return {
                "sessions": session_count,
                "messages": message_count,
                "total_tokens": total_tokens,
                "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
            }

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        """Convert a database row to a Session object."""
        return Session(
            id=row["id"],
            project_path=row["project_path"],
            transcript_path=row["transcript_path"],
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            summary=row["summary"],
            message_count=row["message_count"],
            token_count=row["token_count"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def _row_to_message(self, row: sqlite3.Row) -> Message:
        """Convert a database row to a Message object."""
        return Message(
            id=row["id"],
            session_id=row["session_id"],
            type=MessageType(row["type"]),
            role=row["role"],
            content=row["content"] or "",
            tool_name=row["tool_name"],
            tool_input=json.loads(row["tool_input"]) if row["tool_input"] else None,
            parent_id=row["parent_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            tokens=row["tokens"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )
