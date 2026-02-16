
<img src="https://github.com/ry-ops/aiana/blob/main/Aiana.png" width="100%">

# Aiana

**Personal AI Operations Memory for Claude Code**

Aiana transforms Claude Code from stateless sessions into a compound learning system. It captures conversations, embeds them as vectors, and injects relevant context at session start—so your AI assistant remembers YOUR patterns.

<p align="center">
  <img src="./assets/aiana-flow.svg" alt="Aiana Data Flow" width="100%">
</p>

## The Vision

```
Traditional: Sessions → Do tasks → Forget
With Aiana:  Sessions → Do tasks → Remember → Improve → Compound
```

Every session makes future sessions better. Your workflows get encoded. Your preferences persist. Claude learns YOUR way of working.

---

## Architecture

```mermaid
flowchart TB
    subgraph CC["🖥️ Claude Code"]
        sessions["Sessions & Conversations"]
    end

    subgraph AIANA["🧠 AIANA - Memory Layer"]
        direction TB
        capture["📥 Session Capture"]
        embed["🔢 Embedding Engine<br/><i>all-MiniLM-L6-v2</i>"]
        inject["💉 Context Injector"]
        mcp["🔌 MCP Server"]
    end

    subgraph STORAGE["💾 Storage Backends"]
        direction LR
        sqlite[("📄 SQLite<br/>FTS5 Full-Text")]
        redis[("⚡ Redis<br/>Session Cache")]
        mem0[("🧠 Mem0<br/>AI Memory")]
        qdrant[("🔮 Qdrant<br/>Vector Search")]
    end

    CC -->|"hooks API"| capture
    capture --> embed
    embed --> sqlite
    embed --> redis
    embed --> mem0
    mem0 --> qdrant

    sqlite --> inject
    redis --> inject
    mem0 --> inject

    inject -->|"context block"| CC
    mcp <-->|"tools"| CC

    style AIANA fill:#7C3AED,color:#fff
    style CC fill:#D97706,color:#fff
    style sqlite fill:#0EA5E9,color:#fff
    style redis fill:#DC2626,color:#fff
    style mem0 fill:#EC4899,color:#fff
    style qdrant fill:#059669,color:#fff
```

<p align="center">
  <img src="./assets/aiana-architecture.svg" alt="Aiana Architecture" width="100%">
</p>

---

## Features

### Storage & Search
- **SQLite with FTS5** - Session transcripts, full-text search
- **Redis caching** - Fast session state, context cache, preferences
- **Qdrant vectors** - Semantic search via sentence-transformers
- **Mem0 integration** - Enhanced AI memory with automatic extraction and deduplication

### Intelligence
- **Context injection** - Auto-inject relevant memories at session start
- **User preferences** - Persistent (static) and recent (dynamic) prefs
- **Semantic search** - Find memories by meaning, not just keywords
- **Mem0 memory management** - Automatic memory consolidation and relevance scoring

### Integration
- **MCP server mode** - Expose memory tools directly to Claude
- **Hook-based capture** - Official Claude Code hooks API
- **File watcher** - Docker-compatible monitoring mode
- **Auto-bootstrap** - One-and-done preference loading on first install

### Privacy
- **100% local** - All data stays on your machine
- **No cloud sync** - Nothing leaves your system
- **Read-only mounts** - Docker uses read-only access to Claude data

---

## Quick Start

### Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/ry-ops/aiana
cd aiana

# Start full stack (Aiana + Redis + Qdrant)
docker compose up -d

# Check status
docker compose exec aiana aiana status

# Search memories
docker compose exec aiana aiana memory search "authentication"
```

### Local Installation

```bash
# Install with all features
pip install -e ".[all]"

# Or minimal install
pip install -e .

# Install Claude Code hooks (auto-loads development preferences)
aiana install

# Start monitoring
aiana start
```

> **One-and-Done**: The `aiana install` command automatically bootstraps your development preferences into memory. No manual configuration needed - your standards are immediately active across all projects.

---

## CLI Commands

### Session Management

```bash
# List recent sessions
aiana list --limit 10

# View a session
aiana show <session-id>

# Search full-text
aiana search "database migration"

# Export session
aiana export <session-id> --format markdown
```

### Memory Operations

```bash
# Semantic search
aiana memory search "how did I fix the auth bug"

# Add a memory manually
aiana memory add "cortex uses uv for Python deps" --type pattern

# Recall context for a project
aiana memory recall git-steer
```

### Preferences

```bash
# Add permanent preference
aiana prefer "Uses conventional commits"

# Add temporary/recent context
aiana prefer "Working on Aiana docs" --temporary
```

### Bootstrap

```bash
# Force reload development preferences
aiana bootstrap --force

# Reset bootstrap marker (allows re-bootstrap on next install)
aiana bootstrap --reset
```

### MCP Server

```bash
# Start MCP server
aiana mcp

# Check system status
aiana status
```

---

## MCP Server Tools

When running as an MCP server, Aiana exposes these tools to Claude:

| Tool | Description |
|------|-------------|
| `memory_search` | Semantic search across memories |
| `memory_add` | Save a memory or note |
| `memory_recall` | Get context for a project |
| `memory_feedback` | Rate recalled memories (helpful/not helpful/harmful) |
| `feedback_summary` | Get summary of recall quality patterns |
| `session_list` | List recorded sessions |
| `session_show` | View session details |
| `preference_add` | Add user preferences |
| `aiana_status` | System health check |

### Claude Desktop Integration

```json
{
  "mcpServers": {
    "aiana": {
      "command": "aiana",
      "args": ["mcp"]
    }
  }
}
```

---

## Docker Configuration

### Full Stack (docker-compose.yml)

```yaml
services:
  aiana:
    image: ry-ops/aiana:latest
    depends_on:
      - redis
      - qdrant
    volumes:
      - ~/.claude:/home/aiana/.claude:ro
      - aiana-data:/home/aiana/.aiana
    ports:
      - "8765:8765"  # MCP server
    environment:
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant-data:/qdrant/storage

volumes:
  aiana-data:
  qdrant-data:
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TZ` | Timezone | `UTC` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `QDRANT_URL` | Qdrant server URL | `http://localhost:6333` |
| `AIANA_MCP_PORT` | MCP server port | `8765` |
| `AIANA_EMBEDDING_MODEL` | Embedding model | `all-MiniLM-L6-v2` |

---

## Mem0 Integration

AIANA v1.1.0 integrates [Mem0](https://github.com/mem0ai/mem0) for enhanced AI memory management.

### Why Mem0?

- **Automatic memory extraction** - Extracts key information from conversations
- **Deduplication** - Consolidates related memories automatically
- **Relevance scoring** - Built-in scoring for better retrieval
- **46k+ stars** - Active community, well-maintained

### Integration Strategy

We use the **Wrapper Pattern** with pinned versions:

```toml
# Pinned to major version - allows patches, blocks breaking changes
"mem0ai>=1.0.3,<2.0"
```

```
┌─────────────────────────────────────────────────┐
│              AIANA Storage Layer                │
├─────────────────────────────────────────────────┤
│                                                 │
│   Mem0Storage  ──────►  QdrantStorage           │
│   (primary)             (fallback)              │
│       │                      │                  │
│       ▼                      ▼                  │
│   ┌───────┐              ┌───────┐              │
│   │ Mem0  │──────────────│Qdrant │              │
│   │  API  │   uses       │  API  │              │
│   └───────┘              └───────┘              │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Benefits:**
- **Isolation** - Mem0 API changes stay in `Mem0Storage` wrapper
- **Fallback** - If Mem0 fails, `QdrantStorage` takes over
- **Testability** - Can mock wrapper for testing
- **Swappability** - Replace Mem0 without touching other code

See [ADR-001](docs/decisions/001-dependency-integration-strategy.md) for full rationale.

---

## Configuration

Configuration file: `~/.aiana/config.yaml`

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

---

## How Context Injection Works

On every `SessionStart`, Aiana:

1. **Loads your profile** - Static preferences you've saved
2. **Fetches project context** - Recent work in this project
3. **Searches semantically** - Finds relevant memories
4. **Injects context** - Adds `<aiana-context>` block

```xml
<aiana-context>
## User Preferences (Persistent)
- Prefers TypeScript over JavaScript
- Uses ESLint flat config (v9+)
- Commits with conventional format

## Project: git-steer
### Recent Activity
- Fixed 9 security vulnerabilities
- Updated to vitest 4.x
- Created blog post series

## Recent Context
- Working on Aiana documentation
</aiana-context>
```

Claude sees this context and adapts to YOUR patterns.

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Technical design and components
- [Storage Backends](docs/STORAGE.md) - SQLite, Redis, Qdrant configuration
- [MCP Server](docs/MCP_SERVER.md) - MCP integration and tools
- [Context Injection](docs/CONTEXT_INJECTION.md) - How memory injection works
- [Claude Code Internals](docs/CLAUDE_CODE_INTERNALS.md) - File formats, hooks, APIs
- [TOS Compatibility](docs/TOS_COMPATIBILITY_ANALYSIS.md) - Legal compliance

### Architecture Decisions
- [ADR-001: Dependency Integration Strategy](docs/decisions/001-dependency-integration-strategy.md) - Wrapper pattern for third-party libs

---

## Privacy & Security

Aiana is designed with privacy as a core principle:

- **Local Only** - All data stored on your machine
- **No Cloud Sync** - Data never leaves your system
- **User Control** - You decide what gets recorded
- **Read-Only Access** - Docker mounts Claude directory as read-only
- **Non-Root Container** - Runs as unprivileged user

---

## Roadmap

- [x] **Phase 1: Core MVP**
  - [x] Hook-based session capture
  - [x] SQLite storage with FTS5
  - [x] CLI interface
  - [x] Docker support

- [x] **Phase 2: Memory Layer**
  - [x] Redis caching
  - [x] Qdrant vector storage
  - [x] Semantic search
  - [x] Context injection
  - [x] MCP server mode

- [x] **Phase 2.5: Enhanced Memory (v1.1.0)**
  - [x] Mem0 integration
  - [x] Automatic memory extraction
  - [x] Memory deduplication
  - [x] Conversation-based memory

- [x] **Phase 2.6: Auto-Bootstrap (v1.2.0)**
  - [x] Bundled development preferences
  - [x] Automatic preference loading on first install
  - [x] Cross-project memory (user-level, not project-isolated)
  - [x] One-and-done installation experience

- [ ] **Phase 3: Intelligence**
  - [ ] Automatic pattern extraction
  - [ ] Session summaries
  - [ ] Cross-session linking
  - [ ] Workflow suggestions

- [ ] **Phase 4: Polish**
  - [ ] Secret redaction
  - [ ] Encryption at rest
  - [ ] Web UI (optional)

---

## Related Projects

**ry-ops ecosystem:**
- [git-steer](https://github.com/ry-ops/git-steer) - GitHub autonomy engine via MCP
- [cortex](https://github.com/ry-ops/cortex) - Multi-agent AI system

**Community tools:**
- [ccusage](https://github.com/ryoppippi/ccusage) - Cost/token tracking
- [claude-code-log](https://github.com/daaain/claude-code-log) - JSONL to HTML converter

---

## Contributing

Contributions welcome! Please read the documentation and open an issue before submitting PRs.

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Repository:** [github.com/ry-ops/aiana](https://github.com/ry-ops/aiana)

**Blog Post:** [Personal AI Operations Memory](https://ry-ops.dev/posts/2026-02-01-personal-ai-operations-memory)

**Status:** Phase 2.6 Complete - Auto-Bootstrap Ready

**Version:** [v1.2.1](https://github.com/ry-ops/aiana/releases/tag/v1.2.1)

**Updated:** 2026-02-14

---

## Changelog

### v1.2.1 (2026-02-14)
- Fixed CVE-2026-26007: Bump cryptography to >=46.0.5 (subgroup attack in SECT curves)

### v1.2.0 (2026-02-04)
- **Auto-Bootstrap**: Automatically load development preferences on first `aiana install`
- Added `aiana bootstrap` command for manual preference management
- Bundled `bootstrap/user-preferences.md` with development standards
- Cross-project memory by default (user-level, not project-isolated)
- One-and-done installation experience

### v1.1.0 (2026-02-04)
- Added Mem0 integration for enhanced AI memory management
- Automatic memory extraction from conversations
- Memory consolidation and deduplication
- Mem0 as primary memory backend with Qdrant fallback
- Updated CLI commands to support Mem0
- Updated MCP server tools for Mem0
- Implemented wrapper pattern with pinned dependency (`>=1.0.3,<2.0`)
- Added ADR-001: Dependency Integration Strategy
