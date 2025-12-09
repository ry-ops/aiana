
<img src="https://github.com/ry-ops/aiana/blob/main/aiana.png" width="100%">

# Aiana

**AI Conversation Attendant for Claude Code**

Aiana is a conversation monitoring and recording system that integrates with Claude Code to capture and store conversations locally for review, analysis, and archival.

## TOS Compatibility

**Status: CONDITIONALLY COMPATIBLE** - See [TOS Compatibility Analysis](docs/TOS_COMPATIBILITY_ANALYSIS.md)

Aiana operates within Anthropic's Terms of Service by:
- Recording only YOUR OWN conversations (user owns their data)
- Storing all data locally (no external transmission)
- Using official Claude Code hooks API
- Respecting user privacy and consent

## How It Works

Aiana uses Claude Code's official [Hooks System](https://code.claude.com/docs/en/hooks) to capture conversation events:

```
Claude Code Session
       │
       ├─► SessionStart hook → Aiana registers session
       │
       ├─► File watcher monitors ~/.claude/projects/*.jsonl
       │
       ├─► PostToolUse hooks → Capture tool interactions
       │
       └─► SessionEnd hook → Finalize and index session
```

All data stays on your machine in `~/.aiana/`.

## Features

### Implemented
- [x] Hook-based session capture
- [x] JSONL file monitoring
- [x] Local SQLite storage with FTS5 search
- [x] CLI interface (list, show, search, export)
- [x] Full-text search
- [x] Docker support

### Planned
- [ ] Secret redaction
- [ ] Encryption at rest
- [ ] Session summaries
- [ ] MCP server mode
- [ ] Web UI (optional)

## Quick Start

### Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/ry-ops/aiana
cd aiana

# Start with Docker Compose
docker compose up -d

# View logs
docker compose logs -f

# Run commands
docker compose exec aiana aiana list
docker compose exec aiana aiana search "query"
```

### Docker Run

```bash
# Build image
docker build -t ry-ops/aiana .

# Run container
docker run -d \
  --name aiana \
  -v ~/.claude:/home/aiana/.claude:ro \
  -v aiana-data:/home/aiana/.aiana \
  ry-ops/aiana

# Execute commands
docker exec aiana aiana list
docker exec aiana aiana show <session-id>
docker exec aiana aiana search "authentication"
```

### Local Installation

Requires Python 3.10+

```bash
# Install from source
git clone https://github.com/ry-ops/aiana
cd aiana
pip install -e .

# Install Claude Code hooks
aiana install

# Start monitoring
aiana start
```

## Usage

```bash
# List recent sessions
aiana list --limit 10

# Search conversations
aiana search "database migration"

# View a session
aiana show <session-id>

# Export session
aiana export <session-id> --format markdown > session.md

# Show status
aiana status
```

## Docker Configuration

### docker-compose.yml

```yaml
version: '3.8'

services:
  aiana:
    image: ry-ops/aiana:latest
    container_name: aiana
    restart: unless-stopped
    volumes:
      # Mount Claude Code directory (read-only)
      - ~/.claude:/home/aiana/.claude:ro
      # Persist Aiana data
      - aiana-data:/home/aiana/.aiana
    environment:
      - TZ=America/Chicago

volumes:
  aiana-data:
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TZ` | Timezone | `UTC` |

### Volumes

| Path | Description |
|------|-------------|
| `/home/aiana/.claude` | Claude Code data (mount read-only) |
| `/home/aiana/.aiana` | Aiana database and config |

### Commands

```bash
# Start monitoring (default)
docker compose up -d

# View sessions
docker compose exec aiana aiana list

# Search conversations
docker compose exec aiana aiana search "query"

# Export session
docker compose exec aiana aiana export <id> --format markdown

# Shell access
docker compose exec aiana shell

# View logs
docker compose logs -f aiana
```

## Configuration

Configuration file: `~/.aiana/config.yaml` (or `/home/aiana/.aiana/config.yaml` in Docker)

```yaml
storage:
  type: sqlite
  path: ~/.aiana/conversations.db

recording:
  include_tool_results: true
  include_thinking: false
  redact_secrets: true

retention:
  days: 90
  max_sessions: 1000

privacy:
  encrypt_at_rest: false
```

## Architecture

See [Architecture Documentation](docs/ARCHITECTURE.md) for full technical details.

```
~/.aiana/
├── config.yaml          # Configuration
├── conversations.db     # SQLite database with FTS5
└── exports/             # Exported sessions
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Technical design and components
- [Claude Code Internals](docs/CLAUDE_CODE_INTERNALS.md) - File formats, hooks, APIs
- [Anthropic API Reference](docs/ANTHROPIC_API_REFERENCE.md) - API documentation
- [TOS Compatibility Analysis](docs/TOS_COMPATIBILITY_ANALYSIS.md) - Legal compliance

## Privacy & Security

Aiana is designed with privacy as a core principle:

- **Local Only**: All data stored on your machine
- **No Cloud Sync**: Data never leaves your system
- **User Control**: You decide what gets recorded
- **Read-Only Access**: Docker mounts Claude directory as read-only
- **Non-Root Container**: Runs as unprivileged user
- **Encryption**: Optional encryption at rest (planned)

## Claude Code Integration

For local installation, Aiana integrates via Claude Code's official hooks system:

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{"type": "command", "command": "aiana hook session-start"}]
    }],
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{"type": "command", "command": "aiana hook post-tool"}]
    }],
    "SessionEnd": [{
      "hooks": [{"type": "command", "command": "aiana hook session-end"}]
    }]
  }
}
```

In Docker mode, Aiana uses file watching instead of hooks for monitoring.

## Development

```bash
# Clone repository
git clone https://github.com/ry-ops/aiana
cd aiana

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .
mypy src/

# Build Docker image
docker build -t ry-ops/aiana .
```

## Roadmap

- [x] Phase 0: Research & Documentation
  - [x] Claude Code internals research
  - [x] Anthropic API documentation
  - [x] TOS compatibility analysis
  - [x] Architecture design
- [x] Phase 1: Core MVP
  - [x] Hook handler implementation
  - [x] File watcher
  - [x] SQLite storage with FTS5
  - [x] CLI interface
  - [x] Docker support
- [ ] Phase 2: Enhanced Features
  - [ ] Secret redaction
  - [ ] Encryption at rest
  - [ ] Export formats (HTML)
  - [ ] Session summaries
- [ ] Phase 3: Advanced
  - [ ] MCP server mode
  - [ ] Web UI
  - [ ] Team support

## Related Projects

Community tools for Claude Code conversation management:

- [ccusage](https://github.com/ryoppippi/ccusage) - Cost/token tracking
- [claude-code-log](https://github.com/daaain/claude-code-log) - JSONL to HTML converter
- [claude-history](https://github.com/thejud/claude-history) - History extraction
- [claude-JSONL-browser](https://github.com/withLinda/claude-JSONL-browser) - Web-based viewer

## Contributing

Contributions welcome! Please read the documentation and open an issue before submitting PRs.

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Project**: Part of the [@ry-ops](https://github.com/ry-ops) ecosystem
**Status**: Phase 1 Complete - MVP Ready
**Created**: 2025-10-31
**Updated**: 2025-12-09
