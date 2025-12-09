# Aiana Architecture

This document describes the technical architecture for Aiana, the AI Conversation Attendant for Claude Code.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Code                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Session   │  │    Hooks    │  │   ~/.claude/projects/   │ │
│  │   Manager   │──│   System    │──│      JSONL Files        │ │
│  └─────────────┘  └──────┬──────┘  └───────────┬─────────────┘ │
└──────────────────────────┼─────────────────────┼───────────────┘
                           │                     │
                           ▼                     ▼
┌──────────────────────────────────────────────────────────────────┐
│                          Aiana                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │   Hook Handler   │  │   File Watcher   │  │  Storage Layer │ │
│  │  (SessionStart,  │  │  (inotify/       │  │  (SQLite/      │ │
│  │   PostToolUse)   │  │   fsevents)      │  │   Files)       │ │
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬────────┘ │
│           │                     │                     │          │
│           └─────────────────────┼─────────────────────┘          │
│                                 ▼                                │
│                    ┌─────────────────────┐                       │
│                    │  Conversation Index │                       │
│                    │  (Search, Filter)   │                       │
│                    └──────────┬──────────┘                       │
│                               │                                  │
│           ┌───────────────────┼───────────────────┐              │
│           ▼                   ▼                   ▼              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
│  │   CLI Viewer    │ │   Web Viewer    │ │   Export API    │    │
│  │   (Terminal)    │ │   (Optional)    │ │   (JSON/MD)     │    │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Hook Handler

Integrates with Claude Code's hooks system to capture events in real-time.

**Hooks Configuration** (`~/.claude/settings.json`):

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "aiana hook session-start",
        "timeout": 5
      }]
    }],
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "aiana hook post-tool",
        "timeout": 5
      }]
    }],
    "SessionEnd": [{
      "hooks": [{
        "type": "command",
        "command": "aiana hook session-end",
        "timeout": 5
      }]
    }]
  }
}
```

**Hook Input Processing**:

```python
import json
import sys

def handle_hook():
    """Process hook input from Claude Code."""
    input_data = json.load(sys.stdin)

    session_id = input_data["session_id"]
    transcript_path = input_data["transcript_path"]
    event = input_data["hook_event_name"]

    if event == "SessionStart":
        register_session(session_id, transcript_path)
    elif event == "PostToolUse":
        record_tool_use(session_id, input_data)
    elif event == "SessionEnd":
        finalize_session(session_id)
```

### 2. File Watcher

Monitors JSONL files for changes to capture conversation updates.

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

class TranscriptHandler(FileSystemEventHandler):
    def __init__(self, aiana_storage):
        self.storage = aiana_storage
        self.file_positions = {}

    def on_modified(self, event):
        if event.src_path.endswith('.jsonl'):
            self.process_new_lines(Path(event.src_path))

    def process_new_lines(self, path: Path):
        """Read only new lines since last check."""
        pos = self.file_positions.get(str(path), 0)

        with open(path) as f:
            f.seek(pos)
            for line in f:
                self.storage.append_message(path, json.loads(line))
            self.file_positions[str(path)] = f.tell()

def start_watcher():
    projects_dir = Path.home() / '.claude' / 'projects'
    observer = Observer()
    observer.schedule(TranscriptHandler(), str(projects_dir), recursive=True)
    observer.start()
```

### 3. Storage Layer

Stores conversation data with indexing for search and retrieval.

**Schema (SQLite)**:

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    project_path TEXT NOT NULL,
    transcript_path TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    summary TEXT,
    message_count INTEGER DEFAULT 0,
    token_count INTEGER DEFAULT 0
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'user', 'assistant', 'tool_use', 'tool_result'
    role TEXT,
    content TEXT,
    tool_name TEXT,
    tool_input TEXT,
    parent_id TEXT,
    timestamp TIMESTAMP NOT NULL,
    tokens INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_messages_type ON messages(type);
CREATE INDEX idx_sessions_project ON sessions(project_path);

-- Full-text search
CREATE VIRTUAL TABLE messages_fts USING fts5(
    content,
    content=messages,
    content_rowid=rowid
);
```

**Storage Interface**:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import sqlite3

@dataclass
class Message:
    id: str
    session_id: str
    type: str
    role: Optional[str]
    content: str
    tool_name: Optional[str]
    tool_input: Optional[dict]
    parent_id: Optional[str]
    timestamp: datetime
    tokens: Optional[int]

@dataclass
class Session:
    id: str
    project_path: str
    transcript_path: str
    started_at: datetime
    ended_at: Optional[datetime]
    summary: Optional[str]
    message_count: int
    token_count: int

class AianaStorage:
    def __init__(self, db_path: str = "~/.aiana/conversations.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def create_session(self, session: Session) -> None: ...
    def append_message(self, message: Message) -> None: ...
    def search(self, query: str, project: Optional[str] = None) -> List[Message]: ...
    def get_session(self, session_id: str) -> Session: ...
    def list_sessions(self, project: Optional[str] = None) -> List[Session]: ...
```

### 4. CLI Interface

```
aiana - AI Conversation Attendant for Claude Code

Usage:
  aiana [command]

Commands:
  start         Start monitoring Claude Code sessions
  stop          Stop monitoring
  status        Show monitoring status

  list          List recorded sessions
  show <id>     Display a session transcript
  search <q>    Search across conversations
  export <id>   Export session to file

  hook <event>  Handle Claude Code hook events (internal)

  config        Configure Aiana settings
  install       Install Claude Code hooks

Options:
  -p, --project PATH   Filter by project
  -f, --format FORMAT  Output format (text, json, markdown)
  -v, --verbose        Verbose output
  --help               Show help
```

**Example Commands**:

```bash
# Install Aiana hooks into Claude Code
aiana install

# Start monitoring (daemon mode)
aiana start --daemon

# List recent sessions
aiana list --limit 10

# Search for conversations about "database"
aiana search "database migration"

# Export a session
aiana export abc123 --format markdown > session.md

# Show session details
aiana show abc123 --format json
```

### 5. Configuration

**Config File** (`~/.aiana/config.yaml`):

```yaml
# Aiana Configuration

storage:
  type: sqlite  # sqlite, postgres, files
  path: ~/.aiana/conversations.db

monitoring:
  enabled: true
  auto_start: false  # Start with shell

recording:
  include_tool_results: true
  include_thinking: false  # Extended thinking blocks
  redact_secrets: true

retention:
  days: 90  # 0 for unlimited
  max_sessions: 1000

privacy:
  encrypt_at_rest: false
  encryption_key_path: ~/.aiana/key

export:
  default_format: markdown
  include_metadata: true
```

## Data Flow

### Session Recording Flow

```
1. User starts Claude Code session
   │
2. SessionStart hook fires
   │  └─► Aiana registers session, gets transcript_path
   │
3. User sends prompt
   │  └─► (Captured via file watcher on history.jsonl)
   │
4. Claude processes, uses tools
   │  └─► PostToolUse hooks fire
   │      └─► Aiana records tool usage
   │
5. Claude responds
   │  └─► File watcher detects JSONL update
   │      └─► Aiana parses and stores message
   │
6. Session ends
   │  └─► SessionEnd hook fires
       └─► Aiana finalizes session, generates summary
```

### Search Flow

```
User: aiana search "authentication"
   │
   ▼
┌─────────────────────────────────────┐
│          Full-Text Search           │
│  SELECT * FROM messages_fts         │
│  WHERE messages_fts MATCH 'auth*'   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         Result Aggregation          │
│  - Group by session                 │
│  - Rank by relevance                │
│  - Include context (prev/next)      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         Format & Display            │
│  - Highlight matches                │
│  - Show session metadata            │
│  - Truncate long content            │
└─────────────────────────────────────┘
```

## Security Considerations

### Secret Detection

```python
import re

SECRET_PATTERNS = [
    r'(?i)(api[_-]?key|apikey)["\s:=]+["\']?([a-zA-Z0-9_-]{20,})',
    r'(?i)(password|passwd|pwd)["\s:=]+["\']?([^\s"\']+)',
    r'(?i)(secret|token)["\s:=]+["\']?([a-zA-Z0-9_-]{20,})',
    r'(?i)(aws[_-]?access[_-]?key)["\s:=]+["\']?([A-Z0-9]{20})',
    r'(?i)(private[_-]?key)["\s:=]+["\']?([^\s"\']+)',
]

def redact_secrets(content: str) -> str:
    """Redact potential secrets from content."""
    for pattern in SECRET_PATTERNS:
        content = re.sub(pattern, r'\1=[REDACTED]', content)
    return content
```

### Encryption at Rest

```python
from cryptography.fernet import Fernet

class EncryptedStorage(AianaStorage):
    def __init__(self, key_path: str, **kwargs):
        super().__init__(**kwargs)
        self.fernet = Fernet(self._load_key(key_path))

    def _encrypt(self, data: str) -> bytes:
        return self.fernet.encrypt(data.encode())

    def _decrypt(self, data: bytes) -> str:
        return self.fernet.decrypt(data).decode()
```

## Future Extensions

### MCP Server Mode

Expose Aiana as an MCP server for Claude Code to query its own history:

```python
from mcp import Server, Tool

server = Server("aiana")

@server.tool("search_history")
async def search_history(query: str, limit: int = 10):
    """Search past conversation history."""
    return storage.search(query, limit=limit)

@server.tool("get_session")
async def get_session(session_id: str):
    """Retrieve a specific session."""
    return storage.get_session(session_id)
```

### Web UI

Optional web interface for browsing conversations:

```
http://localhost:3000/aiana
├── /sessions           # Session list
├── /sessions/:id       # Session viewer
├── /search             # Search interface
└── /settings           # Configuration
```

## Dependencies

```toml
[project]
dependencies = [
    "watchdog>=3.0.0",      # File system monitoring
    "click>=8.0.0",         # CLI framework
    "rich>=13.0.0",         # Terminal formatting
    "pyyaml>=6.0",          # Configuration
    "cryptography>=41.0",   # Encryption (optional)
]

[project.optional-dependencies]
web = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
]
mcp = [
    "mcp>=1.0.0",
]
```

## Development Roadmap

### Phase 1: Core (MVP)
- [ ] Hook handler implementation
- [ ] File watcher for JSONL
- [ ] SQLite storage
- [ ] Basic CLI (list, show, search)
- [ ] Install command for hooks

### Phase 2: Enhanced
- [ ] Secret redaction
- [ ] Encryption at rest
- [ ] Export formats (MD, JSON, HTML)
- [ ] Session summaries
- [ ] Retention policies

### Phase 3: Advanced
- [ ] MCP server mode
- [ ] Web UI
- [ ] Team/multi-user support
- [ ] Analytics dashboard
