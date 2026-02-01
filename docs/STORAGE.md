# Storage Backends

Aiana uses a three-layer storage architecture for different use cases:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐
│   SQLite    │    │    Redis    │    │      Qdrant         │
│   (FTS5)    │    │   (Cache)   │    │  (Vector Search)    │
│             │    │             │    │                     │
│ - Sessions  │    │ - Hot data  │    │ - Embeddings        │
│ - Messages  │    │ - Context   │    │ - Semantic search   │
│ - Full-text │    │ - Prefs     │    │ - Similar memories  │
└─────────────┘    └─────────────┘    └─────────────────────┘
```

## SQLite (Primary Storage)

SQLite with FTS5 is the primary storage layer for session transcripts and messages.

### Location

```
~/.aiana/conversations.db
```

### Schema

```sql
-- Sessions table
CREATE TABLE sessions (
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

-- Messages table
CREATE TABLE messages (
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

-- Full-text search
CREATE VIRTUAL TABLE messages_fts USING fts5(
    content,
    content=messages,
    content_rowid=rowid
);
```

### Usage

```python
from aiana.storage import AianaStorage

storage = AianaStorage()

# List sessions
sessions = storage.list_sessions(project="git-steer", limit=10)

# Get messages
messages = storage.get_messages(session_id)

# Full-text search
results = storage.search("authentication bug", limit=20)

# Get stats
stats = storage.get_stats()
```

---

## Redis (Cache Layer)

Redis provides fast caching for session state, context, and preferences.

### Connection

```python
# Environment variable
REDIS_URL=redis://localhost:6379

# Or in code
from aiana.storage.redis import RedisCache
cache = RedisCache(url="redis://localhost:6379")
```

### Key Structure

| Prefix | Purpose | TTL |
|--------|---------|-----|
| `aiana:session:{id}` | Active session state | 24 hours |
| `aiana:context:{project}` | Cached context | 4 hours |
| `aiana:profile:{user}` | User preferences | 7 days |
| `aiana:recent:activities` | Recent activity log | None |

### Session State

```python
# Mark session as active
cache.set_active_session(
    session_id="abc123",
    project="/projects/git-steer",
    metadata={"started_by": "user"}
)

# Get active session
session = cache.get_active_session("abc123")

# Update session
cache.update_session("abc123", {"message_count": 42})

# End session
cache.end_session("abc123")
```

### Context Caching

```python
# Cache generated context
cache.cache_context(
    project="git-steer",
    context="<aiana-context>...</aiana-context>",
    ttl=3600 * 4  # 4 hours
)

# Get cached context
context = cache.get_cached_context("git-steer")

# Invalidate on changes
cache.invalidate_context("git-steer")
```

### User Preferences

```python
# Add preference
cache.add_preference("Uses TypeScript", static=True)
cache.add_preference("Working on docs", static=False)

# Get profile
profile = cache.get_profile()
# {
#   "static": ["Uses TypeScript", ...],
#   "dynamic": ["Working on docs", ...]
# }
```

---

## Qdrant (Vector Storage)

Qdrant stores vector embeddings for semantic search across memories.

### Connection

```python
# Environment variable
QDRANT_URL=http://localhost:6333

# Or in code
from aiana.storage.qdrant import QdrantStorage
from aiana.embeddings import get_embedder

embedder = get_embedder()
qdrant = QdrantStorage(url="http://localhost:6333", embedder=embedder)
```

### Collection

Aiana uses a single collection named `aiana_memories`:

```python
# Collection config
{
    "name": "aiana_memories",
    "vectors": {
        "size": 384,  # all-MiniLM-L6-v2
        "distance": "Cosine"
    }
}
```

### Memory Structure

Each memory point contains:

```python
{
    "id": "uuid",
    "vector": [0.1, 0.2, ...],  # 384 dimensions
    "payload": {
        "content": "The actual memory text",
        "session_id": "abc123",
        "project": "git-steer",
        "memory_type": "conversation|preference|pattern|insight",
        "timestamp": "2026-02-01T12:00:00Z"
    }
}
```

### Adding Memories

```python
# Add a memory
memory_id = qdrant.add_memory(
    content="Fixed security vulnerability by updating qdrant-client",
    session_id="abc123",
    project="git-steer",
    memory_type="pattern",
    metadata={"severity": "critical"}
)
```

### Semantic Search

```python
# Search by meaning
results = qdrant.search(
    query="how did I fix the security issue",
    limit=10,
    project="git-steer",  # optional filter
    min_score=0.5
)

# Results include similarity score
for r in results:
    print(f"{r['score']:.2f}: {r['content'][:100]}")
```

### Memory Types

| Type | Description | Example |
|------|-------------|---------|
| `conversation` | Session transcript excerpts | "User asked about auth, fixed with JWT" |
| `preference` | User preferences | "Uses uv for Python dependencies" |
| `pattern` | Recognized patterns | "Security fixes go through workflow dispatch" |
| `insight` | Derived insights | "This project has frequent qdrant issues" |

---

## Embeddings

Aiana uses sentence-transformers for local embedding generation.

### Default Model

```
all-MiniLM-L6-v2
```
- 384 dimensions
- Fast inference
- Good quality for semantic similarity

### Configuration

```python
# Environment variable
AIANA_EMBEDDING_MODEL=all-MiniLM-L6-v2

# Or in code
from aiana.embeddings import Embedder

embedder = Embedder(model_name="all-MiniLM-L6-v2")
```

### Usage

```python
from aiana.embeddings import get_embedder

embedder = get_embedder()

# Single embedding
vector = embedder.embed("Fix security vulnerability")

# Batch embedding
vectors = embedder.batch_embed([
    "First memory",
    "Second memory",
    "Third memory"
], batch_size=32)

# Similarity
score = embedder.similarity(
    "security fix",
    "vulnerability patch"
)
# 0.87
```

### Device Selection

The embedder auto-detects the best device:

1. CUDA (if available)
2. MPS (Apple Silicon)
3. CPU (fallback)

```python
embedder = Embedder(device="cpu")  # Force CPU
```

---

## Docker Setup

### Full Stack

```yaml
version: '3.8'

services:
  aiana:
    image: ry-ops/aiana:latest
    depends_on:
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    environment:
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 128mb
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

  qdrant:
    image: qdrant/qdrant:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
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

| Configuration | Features |
|---------------|----------|
| SQLite only | Session capture, FTS search |
| SQLite + Redis | + Context caching, preferences |
| SQLite + Qdrant | + Semantic search |
| Full stack | All features |

Missing backends are detected at runtime and features gracefully degrade.
