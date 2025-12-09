# Claude Code Internals Reference

This document details Claude Code's internal architecture, file structures, and extension points relevant to Aiana development.

## Local File Structure

### Primary Directory: `~/.claude/`

```
~/.claude/
├── history.jsonl              # Global prompt history (user inputs only)
├── settings.json              # Global user preferences
├── settings.local.json        # Local settings overrides
├── projects/                  # Per-project conversation storage
│   └── [encoded-path]/        # Path-encoded project directories
│       ├── [uuid].jsonl       # Full conversation sessions
│       └── agent-[id].jsonl   # Subagent conversations
├── agents/                    # Agent configurations
├── debug/                     # Debug logs
├── file-history/              # File change history
├── plans/                     # Plan mode storage
├── session-env/               # Session environment files
├── shell-snapshots/           # Shell state snapshots
├── statsig/                   # Analytics/telemetry
├── todos/                     # Todo list storage
└── ide/                       # IDE integration files
```

### Project-Specific Files

```
project-root/
├── .claude/
│   ├── settings.json          # Project-specific settings
│   ├── settings.local.json    # Local overrides (gitignored)
│   └── commands/              # Custom slash commands
├── CLAUDE.md                  # Project memory/context
└── .mcp.json                  # MCP server configuration
```

## JSONL Format Specifications

### history.jsonl (Global Prompt History)

Contains user prompts only (not full conversations):

```json
{
  "display": "User's prompt text",
  "pastedContents": {},
  "timestamp": 1761749338783,
  "project": "/Users/username/project-path"
}
```

### Session JSONL (Full Conversations)

Each line is a typed event:

#### User Message
```json
{
  "type": "user",
  "parentUuid": "previous-message-uuid",
  "isSidechain": false,
  "userType": "external",
  "cwd": "/current/working/directory",
  "sessionId": "session-uuid",
  "version": "2.0.47",
  "gitBranch": "main",
  "message": {
    "role": "user",
    "content": "User's message"
  },
  "uuid": "message-uuid",
  "timestamp": "2025-12-08T18:13:00.000Z"
}
```

#### Assistant Message
```json
{
  "type": "assistant",
  "parentUuid": "user-message-uuid",
  "message": {
    "id": "msg_xxx",
    "model": "claude-sonnet-4-5-20250929",
    "role": "assistant",
    "content": [
      {"type": "text", "text": "Response text"},
      {"type": "tool_use", "id": "tool_xxx", "name": "Read", "input": {...}}
    ],
    "stop_reason": "end_turn",
    "usage": {
      "input_tokens": 1000,
      "output_tokens": 500,
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 0
    }
  },
  "uuid": "assistant-uuid",
  "timestamp": "2025-12-08T18:13:05.000Z"
}
```

#### Summary
```json
{
  "type": "summary",
  "summary": "Brief description of conversation",
  "leafUuid": "last-message-uuid"
}
```

#### File History Snapshot
```json
{
  "type": "file-history-snapshot",
  "messageId": "message-uuid",
  "snapshot": {
    "messageId": "message-uuid",
    "trackedFileBackups": {},
    "timestamp": "2025-12-08T18:13:00.000Z"
  },
  "isSnapshotUpdate": false
}
```

### Path Encoding

Directory paths are encoded by replacing `/` with `-`:
- `/Users/ryandahlberg/Projects/aiana` → `-Users-ryandahlberg-Projects-aiana`

## Hooks System

### Configuration Location

Hooks are configured in `settings.json` (global or project-level):

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolPattern",
        "hooks": [
          {
            "type": "command",
            "command": "your-command-here",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

### Available Hook Events

| Event | Purpose | Matcher Support |
|-------|---------|-----------------|
| `PreToolUse` | Before tool execution | Yes |
| `PostToolUse` | After tool completes | Yes |
| `PermissionRequest` | Permission dialog shown | Yes |
| `Notification` | Notifications sent | Yes |
| `UserPromptSubmit` | User submits prompt | No |
| `Stop` | Agent finishes | No |
| `SubagentStop` | Subagent finishes | No |
| `PreCompact` | Before context compaction | Yes |
| `SessionStart` | Session begins | Yes |
| `SessionEnd` | Session ends | No |

### Hook Input (stdin JSON)

All hooks receive this JSON via stdin:

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "default|plan|acceptEdits|bypassPermissions",
  "hook_event_name": "EventName"
}
```

**Key field for Aiana**: `transcript_path` provides the path to the current session's JSONL transcript.

### Hook Output (stdout JSON)

```json
{
  "decision": "approve|block|deny|allow|ask",
  "reason": "Explanation",
  "continue": true,
  "suppressOutput": false,
  "hookSpecificOutput": {
    "hookEventName": "EventName",
    "additionalContext": "Context to add"
  }
}
```

### Environment Variables in Hooks

- `CLAUDE_PROJECT_DIR`: Project root directory
- `CLAUDE_ENV_FILE`: File path for persisting environment variables
- `CLAUDE_CODE_REMOTE`: "true" for web, empty for CLI
- `CLAUDE_PLUGIN_ROOT`: Plugin directory path

## MCP Integration

### Server Configuration

MCP servers are configured in `.mcp.json` or `settings.json`:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "python",
      "args": ["server.py"],
      "env": {
        "API_KEY": "xxx"
      }
    }
  }
}
```

### Tool Naming Pattern

MCP tools appear with pattern: `mcp__<server>__<tool>`

Example matchers:
- `mcp__memory__.*` - All tools from memory server
- `mcp__.*__write.*` - Write tools from any server

## Data Privacy & Telemetry

### Telemetry Services

| Service | Data Collected | Opt-out |
|---------|---------------|---------|
| Statsig | Latency, usage patterns (NOT code) | `DISABLE_TELEMETRY=1` |
| Sentry | Error logs | `DISABLE_ERROR_REPORTING=1` |
| /bug | Full conversation (explicit) | `DISABLE_BUG_COMMAND=1` |

### Disable All Non-Essential Traffic

```bash
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

### Data Retention

| User Type | Default Retention |
|-----------|------------------|
| Consumer (Free/Pro/Max) | 30 days (opt-out) / 5 years (opt-in) |
| Commercial (Team/Enterprise) | 30 days |
| API (Zero retention) | No server storage |

## Aiana Integration Points

### Recommended Approach: Hooks + File Monitoring

1. **SessionStart Hook**: Get initial `transcript_path`
2. **File Watcher**: Monitor JSONL files for changes
3. **PostToolUse Hook**: Capture tool outputs in real-time
4. **SessionEnd Hook**: Finalize session recording

### Alternative: Direct File Reading

Read JSONL files from `~/.claude/projects/` for historical access:

```python
import json
from pathlib import Path

def read_session(session_path: Path) -> list[dict]:
    """Read a Claude Code session transcript."""
    messages = []
    with open(session_path) as f:
        for line in f:
            messages.append(json.loads(line))
    return messages
```

### Session Discovery

```python
def list_sessions(project_path: str) -> list[Path]:
    """List all sessions for a project."""
    encoded = project_path.replace('/', '-')
    sessions_dir = Path.home() / '.claude' / 'projects' / encoded
    return list(sessions_dir.glob('*.jsonl'))
```

## References

- [Claude Code Hooks Documentation](https://code.claude.com/docs/en/hooks)
- [Claude Code Data Usage](https://code.claude.com/docs/en/data-usage)
- [MCP Integration](https://docs.anthropic.com/en/docs/claude-code/mcp)
