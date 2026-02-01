# Aiana Architecture

This document describes the technical architecture for Aiana, the Personal AI Operations Memory for Claude Code.

## System Overview

Aiana transforms Claude Code from stateless sessions into a compound learning system. Every session makes future sessions better through persistent memory, semantic search, and intelligent context injection.

```
┌──────────────────────────────────────────────────────────────────┐
│                            AIANA                                  │
│                                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐   │
│  │   SQLite    │    │    Redis    │    │      Qdrant         │   │
│  │   (FTS5)    │    │   (Cache)   │    │  (Vector Search)    │   │
│  │             │    │             │    │                     │   │
│  │ - Sessions  │    │ - Hot data  │    │ - Embeddings        │   │
│  │ - Messages  │    │ - Context   │    │ - Semantic search   │   │
│  │ - Full-text │    │ - Prefs     │    │ - Similar memories  │   │
│  └─────────────┘    └─────────────┘    └─────────────────────┘   │
│         │                  │                     │                │
│         └──────────────────┼─────────────────────┘                │
│                            ▼                                      │
│                  ┌─────────────────┐                              │
│                  │ Context Injector│                              │
│                  │                 │                              │
│                  │ SessionStart →  │                              │
│                  │ Inject memories │                              │
│                  └────────┬────────┘                              │
│                           │                                       │
│         ┌─────────────────┼─────────────────┐                     │
│         ▼                 ▼                 ▼                     │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐             │
│  │ MCP Server  │   │     CLI     │   │    Hooks    │             │
│  │  (7 tools)  │   │  Interface  │   │   Handler   │             │
│  └─────────────┘   └─────────────┘   └─────────────┘             │
└──────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Three-Layer Storage

Aiana uses a three-layer storage architecture optimized for different use cases:

| Layer | Technology | Purpose | TTL |
|-------|------------|---------|-----|
| Primary | SQLite + FTS5 | Sessions, messages, full-text search | Permanent |
| Cache | Redis | Hot data, context, preferences | Hours/Days |
| Vectors | Qdrant | Semantic search, embeddings | Permanent |

```
Query Flow:

User: "How did I fix the auth bug?"
       │
       ▼
┌─────────────────┐     ┌─────────────────┐
│  Redis Cache    │ ──► │  Return cached  │
│  (cache hit?)   │     │  context        │
└────────┬────────┘     └─────────────────┘
         │ miss
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Qdrant Search  │ ──► │  Semantic       │
│  (vectors)      │     │  matches        │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  SQLite FTS5    │ ──► │  Full-text      │
│  (full-text)    │     │  matches        │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│  Merge & Rank   │
│  Results        │
└─────────────────┘
```

---

### 2. Context Injector

The Context Injector is Aiana's intelligence layer. It automatically injects relevant memories at session start.

```
┌─────────────────────────────────────────────────────────────────┐
│                      SessionStart Hook                          │
│                                                                 │
│  1. User starts Claude Code session                             │
│                         │                                       │
│                         ▼                                       │
│  2. Aiana hook triggers ──► ContextInjector                     │
│                         │                                       │
│                         ▼                                       │
│  3. Load user profile (Redis)                                   │
│     - Static preferences (permanent)                            │
│     - Dynamic context (recent)                                  │
│                         │                                       │
│                         ▼                                       │
│  4. Fetch project context                                       │
│     - Recent sessions (SQLite)                                  │
│     - Relevant memories (Qdrant)                                │
│                         │                                       │
│                         ▼                                       │
│  5. Format and inject <aiana-context>                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Generated Context Format:**

```xml
<aiana-context>
The following context is recalled from your previous sessions.
Use this to inform your responses but don't explicitly reference it.

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

---

### 3. MCP Server

Aiana exposes memory operations as MCP tools for direct Claude integration.

```
┌─────────────────┐         ┌─────────────────┐
│  Claude Code    │  MCP    │     Aiana       │
│                 │ ◄─────► │   MCP Server    │
│  "Search my     │         │                 │
│   memories"     │         │  ┌───────────┐  │
└─────────────────┘         │  │  7 Tools  │  │
                            │  └───────────┘  │
                            └─────────────────┘
```

**Available Tools:**

| Tool | Purpose |
|------|---------|
| `memory_search` | Semantic search across memories |
| `memory_add` | Save a memory or note |
| `memory_recall` | Get context for a project |
| `session_list` | List recorded sessions |
| `session_show` | View session details |
| `preference_add` | Add user preferences |
| `aiana_status` | System health check |

---

### 4. Embeddings System

Local embedding generation using sentence-transformers.

```python
from aiana.embeddings import get_embedder

embedder = get_embedder()

# Single embedding
vector = embedder.embed("Fix security vulnerability")
# → [0.1, 0.2, ...] (384 dimensions)

# Similarity scoring
score = embedder.similarity("security fix", "vulnerability patch")
# → 0.87
```

**Default Model:** `all-MiniLM-L6-v2`
- 384 dimensions
- Fast inference
- Good semantic similarity

**Device Selection:** Auto-detects CUDA > MPS (Apple Silicon) > CPU

---

### 5. Profile System

User preferences stored in Redis with two categories:

**Static Preferences:**
- Long-term, persistent (7-day TTL)
- Language preferences, frameworks, code style
- Example: "Uses TypeScript for new projects"

**Dynamic Context:**
- Recent, temporary (20 item limit, FIFO)
- Current work focus
- Example: "Working on Aiana docs"

```python
# Profile structure in Redis
{
    "static": [
        "Uses TypeScript over JavaScript",
        "Prefers conventional commits",
        "Uses uv for Python dependencies"
    ],
    "dynamic": [
        "Working on Aiana documentation",
        "Debugging Redis connection"
    ]
}
```

---

## Hook Integration

Aiana integrates with Claude Code's hooks system for real-time capture.

**Configuration** (`~/.claude/settings.json`):

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

---

## Data Flows

### Session Recording

```
1. User starts Claude Code session
   │
2. SessionStart hook fires
   │  └─► Aiana: Register session, inject context
   │      └─► Return <aiana-context> block
   │
3. User sends prompts, Claude responds
   │  └─► File watcher captures JSONL updates
   │      └─► Aiana stores messages in SQLite
   │
4. Claude uses tools
   │  └─► PostToolUse hooks fire
   │      └─► Aiana records tool usage
   │
5. Session ends
   │  └─► SessionEnd hook fires
       └─► Aiana: Finalize session
           └─► Generate summary
           └─► Extract memories → Qdrant
           └─► Invalidate cached context
```

### Memory Search

```
User: aiana memory search "authentication bug fix"
   │
   ▼
┌─────────────────────────────────────┐
│         Semantic Search             │
│  1. Generate query embedding        │
│  2. Search Qdrant for similar       │
│  3. Filter by project (optional)    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         FTS Fallback                │
│  If Qdrant unavailable:             │
│  SELECT * FROM messages_fts         │
│  WHERE messages_fts MATCH 'auth*'   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         Result Aggregation          │
│  - Merge semantic + FTS results     │
│  - Rank by score                    │
│  - Include context metadata         │
└─────────────────────────────────────┘
```

### Context Generation

```
Session starts for project: git-steer
   │
   ▼
┌─────────────────────────────────────┐
│         Check Cache                 │
│  Redis: aiana:context:git-steer     │
│  TTL: 4 hours                       │
└──────────────┬──────────────────────┘
               │ miss
               ▼
┌─────────────────────────────────────┐
│         Load User Profile           │
│  Redis: aiana:profile:{user}        │
│  - Static preferences               │
│  - Dynamic context                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         Fetch Project Context       │
│  SQLite: Recent sessions            │
│  Qdrant: Relevant memories          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         Generate & Cache            │
│  Format <aiana-context>             │
│  Cache in Redis (4h TTL)            │
└─────────────────────────────────────┘
```

---

## Docker Architecture

### Full Stack Deployment

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
    environment:
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 128mb

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant-data:/qdrant/storage
```

### Resource Limits

| Service | CPU | Memory |
|---------|-----|--------|
| Aiana | 1.0 | 512MB |
| Redis | 0.25 | 192MB |
| Qdrant | 0.5 | 512MB |

---

## Graceful Degradation

Aiana works with any combination of backends:

| Configuration | Available Features |
|---------------|-------------------|
| SQLite only | Session capture, FTS search, CLI |
| SQLite + Redis | + Context caching, preferences, hot data |
| SQLite + Qdrant | + Semantic search, vector memories |
| Full stack | All features |

Missing backends are detected at runtime and features degrade gracefully.

---

## Security Considerations

### Privacy by Design

- **Local Only** - All data stored on your machine
- **No Cloud Sync** - Data never leaves your system
- **Read-Only Access** - Docker mounts Claude directory as read-only
- **Non-Root Container** - Runs as unprivileged user

### Secret Detection

```python
SECRET_PATTERNS = [
    r'(?i)(api[_-]?key|apikey)["\s:=]+["\']?([a-zA-Z0-9_-]{20,})',
    r'(?i)(password|passwd|pwd)["\s:=]+["\']?([^\s"\']+)',
    r'(?i)(secret|token)["\s:=]+["\']?([a-zA-Z0-9_-]{20,})',
    r'(?i)(aws[_-]?access[_-]?key)["\s:=]+["\']?([A-Z0-9]{20})',
]

def redact_secrets(content: str) -> str:
    for pattern in SECRET_PATTERNS:
        content = re.sub(pattern, r'\1=[REDACTED]', content)
    return content
```

### Encryption at Rest (Future)

```python
from cryptography.fernet import Fernet

class EncryptedStorage(AianaStorage):
    def __init__(self, key_path: str, **kwargs):
        super().__init__(**kwargs)
        self.fernet = Fernet(self._load_key(key_path))
```

---

## Dependencies

```toml
[project.dependencies]
watchdog = ">=3.0.0"      # File system monitoring
click = ">=8.0.0"         # CLI framework
rich = ">=13.0.0"         # Terminal formatting
pyyaml = ">=6.0"          # Configuration

[project.optional-dependencies]
redis = ["redis>=5.0.0"]
vector = [
    "qdrant-client>=1.7.0",
    "sentence-transformers>=2.2.0",
]
mcp = ["mcp>=1.0.0"]
all = ["aiana[redis,vector,mcp]"]
```

---

## Development Roadmap

### Phase 1: Core MVP
- [x] Hook handler implementation
- [x] File watcher for JSONL
- [x] SQLite storage with FTS5
- [x] Basic CLI (list, show, search)
- [x] Install command for hooks
- [x] Docker support

### Phase 2: Memory Layer
- [x] Redis caching
- [x] Qdrant vector storage
- [x] Sentence-transformers embeddings
- [x] Semantic search
- [x] Context injection
- [x] MCP server mode
- [x] User preferences (static/dynamic)

### Phase 3: Intelligence
- [ ] Automatic pattern extraction
- [ ] Session summaries (LLM-generated)
- [ ] Cross-session linking
- [ ] Workflow suggestions
- [ ] Memory importance scoring

### Phase 4: Polish
- [ ] Secret redaction
- [ ] Encryption at rest
- [ ] Web UI (optional)
- [ ] Analytics dashboard
- [ ] Export formats (HTML, PDF)

---

## Related Documentation

- [Storage Backends](STORAGE.md) - SQLite, Redis, Qdrant configuration
- [MCP Server](MCP_SERVER.md) - MCP tools and Claude integration
- [Context Injection](CONTEXT_INJECTION.md) - How memory injection works
- [Claude Code Internals](CLAUDE_CODE_INTERNALS.md) - File formats, hooks, APIs
- [TOS Compatibility](TOS_COMPATIBILITY_ANALYSIS.md) - Legal compliance

---

**Status:** Phase 2 Complete - Memory Layer Ready

**Updated:** 2026-02-01
