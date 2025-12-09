"""Hook handlers for Claude Code integration."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from aiana.config import get_claude_dir, load_config
from aiana.models import HookInput, Message, Session
from aiana.storage import AianaStorage


class HookHandler:
    """Handles Claude Code hook events."""

    def __init__(self, storage: Optional[AianaStorage] = None):
        """Initialize hook handler."""
        self.storage = storage or AianaStorage()
        self.config = load_config()

    def handle_stdin(self) -> dict:
        """Read and handle hook input from stdin."""
        try:
            input_data = json.load(sys.stdin)
            hook_input = HookInput.from_json(input_data)
            return self.handle(hook_input)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON input"}
        except Exception as e:
            return {"error": str(e)}

    def handle(self, hook_input: HookInput) -> dict:
        """Handle a hook event."""
        event = hook_input.hook_event_name

        handlers = {
            "SessionStart": self._handle_session_start,
            "SessionEnd": self._handle_session_end,
            "PostToolUse": self._handle_post_tool_use,
            "UserPromptSubmit": self._handle_user_prompt,
            "PreToolUse": self._handle_pre_tool_use,
        }

        handler = handlers.get(event)
        if handler:
            return handler(hook_input)

        return {}

    def _handle_session_start(self, hook_input: HookInput) -> dict:
        """Handle SessionStart event."""
        # Decode project path from transcript path
        project_path = self._decode_project_path(hook_input.transcript_path)

        session = Session(
            id=hook_input.session_id,
            project_path=project_path,
            transcript_path=hook_input.transcript_path,
            started_at=datetime.now(),
            metadata={
                "cwd": hook_input.cwd,
                "permission_mode": hook_input.permission_mode,
            },
        )

        self.storage.create_session(session)

        # Import existing messages from transcript if it exists
        self._import_transcript(hook_input.session_id, hook_input.transcript_path)

        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"[Aiana] Recording session {hook_input.session_id[:8]}...",
            }
        }

    def _handle_session_end(self, hook_input: HookInput) -> dict:
        """Handle SessionEnd event."""
        # Generate summary from messages
        messages = self.storage.get_messages(hook_input.session_id, limit=5)
        summary = None
        if messages:
            # Use first user message as summary
            user_messages = [m for m in messages if m.role == "user"]
            if user_messages:
                summary = user_messages[0].content[:200]

        self.storage.end_session(hook_input.session_id, summary=summary)

        return {}

    def _handle_post_tool_use(self, hook_input: HookInput) -> dict:
        """Handle PostToolUse event."""
        if hook_input.tool_name and hook_input.tool_output:
            # Record tool usage
            message = Message(
                id=f"{hook_input.session_id}-{datetime.now().timestamp()}",
                session_id=hook_input.session_id,
                type="tool_result",
                content=hook_input.tool_output[:10000],  # Limit size
                timestamp=datetime.now(),
                tool_name=hook_input.tool_name,
                tool_input=hook_input.tool_input,
            )
            self.storage.append_message(message)

        return {}

    def _handle_user_prompt(self, hook_input: HookInput) -> dict:
        """Handle UserPromptSubmit event."""
        # This event doesn't provide the prompt content directly
        # We rely on file watching for that
        return {}

    def _handle_pre_tool_use(self, hook_input: HookInput) -> dict:
        """Handle PreToolUse event - just pass through."""
        return {}

    def _decode_project_path(self, transcript_path: str) -> str:
        """Decode project path from transcript path."""
        # Transcript paths look like:
        # ~/.claude/projects/-Users-username-project/session.jsonl
        path = Path(transcript_path)

        if path.parent.name.startswith("-"):
            # Encoded path: -Users-username-project -> /Users/username/project
            encoded = path.parent.name
            return encoded.replace("-", "/")

        return str(path.parent)

    def _import_transcript(self, session_id: str, transcript_path: str) -> None:
        """Import existing messages from a transcript file."""
        path = Path(transcript_path)
        if not path.exists():
            return

        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        message = Message.from_jsonl(session_id, data)
                        if message:
                            self.storage.append_message(message)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass  # Silently fail on import errors


def get_hooks_config() -> dict:
    """Get the hooks configuration for Claude Code."""
    return {
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "aiana hook session-start",
                            "timeout": 5,
                        }
                    ]
                }
            ],
            "SessionEnd": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "aiana hook session-end",
                            "timeout": 5,
                        }
                    ]
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "aiana hook post-tool",
                            "timeout": 5,
                        }
                    ]
                }
            ],
        }
    }


def install_hooks(force: bool = False) -> bool:
    """Install Aiana hooks into Claude Code settings."""
    claude_dir = get_claude_dir()
    settings_path = claude_dir / "settings.json"

    # Read existing settings
    existing = {}
    if settings_path.exists():
        try:
            with open(settings_path) as f:
                existing = json.load(f)
        except json.JSONDecodeError:
            existing = {}

    # Check if hooks already exist
    if "hooks" in existing and not force:
        # Check if our hooks are already there
        hooks = existing.get("hooks", {})
        if "SessionStart" in hooks:
            for hook_group in hooks["SessionStart"]:
                for hook in hook_group.get("hooks", []):
                    if "aiana" in hook.get("command", ""):
                        return False  # Already installed

    # Merge hooks
    aiana_hooks = get_hooks_config()["hooks"]
    existing_hooks = existing.get("hooks", {})

    for event, hook_configs in aiana_hooks.items():
        if event not in existing_hooks:
            existing_hooks[event] = []
        existing_hooks[event].extend(hook_configs)

    existing["hooks"] = existing_hooks

    # Write settings
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "w") as f:
        json.dump(existing, f, indent=2)

    return True


def uninstall_hooks() -> bool:
    """Remove Aiana hooks from Claude Code settings."""
    claude_dir = get_claude_dir()
    settings_path = claude_dir / "settings.json"

    if not settings_path.exists():
        return False

    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except json.JSONDecodeError:
        return False

    if "hooks" not in settings:
        return False

    # Remove Aiana hooks
    modified = False
    for event in list(settings["hooks"].keys()):
        hook_configs = settings["hooks"][event]
        new_configs = []
        for config in hook_configs:
            new_hooks = []
            for hook in config.get("hooks", []):
                if "aiana" not in hook.get("command", ""):
                    new_hooks.append(hook)
            if new_hooks:
                config["hooks"] = new_hooks
                new_configs.append(config)
            else:
                modified = True

        if new_configs:
            settings["hooks"][event] = new_configs
        else:
            del settings["hooks"][event]
            modified = True

    if modified:
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

    return modified
