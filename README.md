
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
- [ ] Hook-based session capture
- [ ] JSONL file monitoring
- [ ] Local SQLite storage
- [ ] CLI interface
- [ ] Full-text search

### Planned
- [ ] Secret redaction
- [ ] Encryption at rest
- [ ] Export (Markdown, JSON, HTML)
- [ ] Session summaries
- [ ] MCP server mode
- [ ] Web UI (optional)

## Installation

```bash
# Install Aiana
pip install aiana  # Coming soon

# Or from source
git clone https://github.com/ry-ops/aiana
cd aiana
pip install -e .

# Install Claude Code hooks
aiana install
```

## Usage

```bash
# Start monitoring (daemon mode)
aiana start --daemon

# List recent sessions
aiana list --limit 10

# Search conversations
aiana search "database migration"

# View a session
aiana show <session-id>

# Export session
aiana export <session-id> --format markdown > session.md
```

## Configuration

Create `~/.aiana/config.yaml`:

```yaml
storage:
  type: sqlite
  path: ~/.aiana/conversations.db

recording:
  include_tool_results: true
  redact_secrets: true

retention:
  days: 90
```

## Architecture

See [Architecture Documentation](docs/ARCHITECTURE.md) for full technical details.

```
~/.aiana/
├── config.yaml          # Configuration
├── conversations.db     # SQLite database
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
- **Secret Redaction**: Automatic detection and redaction of sensitive data
- **Encryption**: Optional encryption at rest
- **Consent**: Explicit opt-in required

## Claude Code Integration

Aiana integrates via Claude Code's official hooks system:

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
```

## Roadmap

- [x] Phase 0: Research & Documentation
  - [x] Claude Code internals research
  - [x] Anthropic API documentation
  - [x] TOS compatibility analysis
  - [x] Architecture design
- [ ] Phase 1: Core MVP
  - [ ] Hook handler implementation
  - [ ] File watcher
  - [ ] SQLite storage
  - [ ] Basic CLI
- [ ] Phase 2: Enhanced Features
  - [ ] Secret redaction
  - [ ] Encryption
  - [ ] Export formats
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
**Status**: Phase 0 Complete - Ready for Implementation
**Created**: 2025-10-31
**Updated**: 2025-12-08
