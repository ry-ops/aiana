"""Configuration management for Aiana."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class StorageConfig:
    """Storage configuration."""

    type: str = "sqlite"
    path: str = "~/.aiana/conversations.db"

    @property
    def resolved_path(self) -> Path:
        """Get resolved path with ~ expansion."""
        return Path(self.path).expanduser()


@dataclass
class RecordingConfig:
    """Recording configuration."""

    include_tool_results: bool = True
    include_thinking: bool = False
    redact_secrets: bool = True


@dataclass
class RetentionConfig:
    """Data retention configuration."""

    days: int = 90  # 0 for unlimited
    max_sessions: int = 1000


@dataclass
class PrivacyConfig:
    """Privacy configuration."""

    encrypt_at_rest: bool = False
    encryption_key_path: str = "~/.aiana/key"


@dataclass
class AianaConfig:
    """Main configuration for Aiana."""

    storage: StorageConfig = field(default_factory=StorageConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    retention: RetentionConfig = field(default_factory=RetentionConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AianaConfig":
        """Create config from dictionary."""
        storage_data = data.get("storage", {})
        recording_data = data.get("recording", {})
        retention_data = data.get("retention", {})
        privacy_data = data.get("privacy", {})

        return cls(
            storage=StorageConfig(**storage_data) if storage_data else StorageConfig(),
            recording=RecordingConfig(**recording_data) if recording_data else RecordingConfig(),
            retention=RetentionConfig(**retention_data) if retention_data else RetentionConfig(),
            privacy=PrivacyConfig(**privacy_data) if privacy_data else PrivacyConfig(),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "storage": {
                "type": self.storage.type,
                "path": self.storage.path,
            },
            "recording": {
                "include_tool_results": self.recording.include_tool_results,
                "include_thinking": self.recording.include_thinking,
                "redact_secrets": self.recording.redact_secrets,
            },
            "retention": {
                "days": self.retention.days,
                "max_sessions": self.retention.max_sessions,
            },
            "privacy": {
                "encrypt_at_rest": self.privacy.encrypt_at_rest,
                "encryption_key_path": self.privacy.encryption_key_path,
            },
        }


def get_config_path() -> Path:
    """Get the path to the config file."""
    return Path.home() / ".aiana" / "config.yaml"


def load_config(config_path: Optional[Path] = None) -> AianaConfig:
    """Load configuration from file."""
    path = config_path or get_config_path()

    if not path.exists():
        return AianaConfig()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return AianaConfig.from_dict(data)


def save_config(config: AianaConfig, config_path: Optional[Path] = None) -> None:
    """Save configuration to file."""
    path = config_path or get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)


def get_aiana_dir() -> Path:
    """Get the Aiana data directory."""
    path = Path.home() / ".aiana"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_claude_dir() -> Path:
    """Get the Claude Code data directory."""
    return Path.home() / ".claude"


def get_claude_projects_dir() -> Path:
    """Get the Claude Code projects directory."""
    return get_claude_dir() / "projects"
