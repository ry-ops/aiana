"""Data models for Aiana."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class MessageType(str, Enum):
    """Types of messages in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    SUMMARY = "summary"
    SYSTEM = "system"


@dataclass
class Message:
    """A single message in a conversation."""

    id: str
    session_id: str
    type: MessageType
    content: str
    timestamp: datetime
    role: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[dict[str, Any]] = None
    parent_id: Optional[str] = None
    tokens: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_jsonl(cls, session_id: str, data: dict[str, Any]) -> Optional["Message"]:
        """Create a Message from a JSONL line."""
        msg_type = data.get("type", "")

        if msg_type == "user":
            message_data = data.get("message", {})
            return cls(
                id=data.get("uuid", ""),
                session_id=session_id,
                type=MessageType.USER,
                content=message_data.get("content", ""),
                timestamp=cls._parse_timestamp(data.get("timestamp")),
                role="user",
                parent_id=data.get("parentUuid"),
                metadata={
                    "cwd": data.get("cwd"),
                    "git_branch": data.get("gitBranch"),
                    "version": data.get("version"),
                },
            )

        elif msg_type == "assistant":
            message_data = data.get("message", {})
            content_blocks = message_data.get("content", [])

            # Extract text content
            text_parts = []
            tool_use = None
            for block in content_blocks:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        tool_use = block
                elif isinstance(block, str):
                    text_parts.append(block)

            usage = message_data.get("usage", {})
            tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

            msg = cls(
                id=data.get("uuid", ""),
                session_id=session_id,
                type=MessageType.ASSISTANT,
                content="\n".join(text_parts),
                timestamp=cls._parse_timestamp(data.get("timestamp")),
                role="assistant",
                parent_id=data.get("parentUuid"),
                tokens=tokens if tokens > 0 else None,
                metadata={
                    "model": message_data.get("model"),
                    "stop_reason": message_data.get("stop_reason"),
                },
            )

            # If there's a tool use, we might want to track it separately
            if tool_use:
                msg.tool_name = tool_use.get("name")
                msg.tool_input = tool_use.get("input")
                msg.type = MessageType.TOOL_USE

            return msg

        elif msg_type == "summary":
            return cls(
                id=data.get("leafUuid", ""),
                session_id=session_id,
                type=MessageType.SUMMARY,
                content=data.get("summary", ""),
                timestamp=datetime.now(),
            )

        return None

    @staticmethod
    def _parse_timestamp(ts: Any) -> datetime:
        """Parse timestamp from various formats."""
        if ts is None:
            return datetime.now()
        if isinstance(ts, (int, float)):
            # Unix timestamp in milliseconds
            return datetime.fromtimestamp(ts / 1000)
        if isinstance(ts, str):
            # ISO format
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return datetime.now()
        return datetime.now()


@dataclass
class Session:
    """A conversation session."""

    id: str
    project_path: str
    transcript_path: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    summary: Optional[str] = None
    message_count: int = 0
    token_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get session duration in seconds."""
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    @property
    def is_active(self) -> bool:
        """Check if session is still active."""
        return self.ended_at is None


@dataclass
class HookInput:
    """Input data from a Claude Code hook."""

    session_id: str
    transcript_path: str
    cwd: str
    hook_event_name: str
    permission_mode: str = "default"
    tool_name: Optional[str] = None
    tool_input: Optional[dict[str, Any]] = None
    tool_output: Optional[str] = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "HookInput":
        """Create HookInput from JSON data."""
        return cls(
            session_id=data.get("session_id", ""),
            transcript_path=data.get("transcript_path", ""),
            cwd=data.get("cwd", ""),
            hook_event_name=data.get("hook_event_name", ""),
            permission_mode=data.get("permission_mode", "default"),
            tool_name=data.get("tool_name"),
            tool_input=data.get("tool_input"),
            tool_output=data.get("tool_output"),
        )
