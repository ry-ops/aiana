# Context Injection

Context injection is Aiana's core intelligence feature. It automatically injects relevant memories and preferences at the start of each Claude Code session.

## How It Works

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
│     - Static preferences                                        │
│     - Dynamic/recent context                                    │
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

## Context Format

```xml
<aiana-context>
The following context is recalled from your previous sessions.
Use this to inform your responses but don't explicitly reference it.

## User Preferences (Persistent)
- Prefers TypeScript over JavaScript
- Uses ESLint flat config (v9+)
- Commits with conventional format
- Uses uv for Python dependencies

## Project: git-steer
### Recent Activity
- Fixed 9 security vulnerabilities
- Updated to vitest 4.x
- Created blog post series

## Recent Context
- Working on Aiana documentation
- Last session: security sweep across repos
</aiana-context>
```

## Profile System

### Static Preferences

Long-term, persistent preferences that rarely change:

```python
# Add static preference
injector.add_preference("Uses TypeScript over JavaScript", static=True)
injector.add_preference("Prefers conventional commits", static=True)
```

These are stored in Redis with a 7-day TTL and typically represent:
- Language preferences
- Framework choices
- Code style conventions
- Workflow patterns

### Dynamic Context

Recent, temporary context that changes frequently:

```python
# Add dynamic context
injector.add_preference("Working on Aiana docs", static=False)
injector.add_preference("Debugging Redis connection", static=False)
```

Dynamic context:
- Limited to 20 items (oldest removed when exceeded)
- Represents current work focus
- Automatically updated from sessions

## Project Context

### From SQLite (Sessions)

```python
# Recent sessions for this project
sessions = sqlite.list_sessions(project="git-steer", limit=5)

# Generates:
# ### Recent Sessions
# - 2026-02-01 10:00: 47 messages
# - 2026-01-31 14:30: 23 messages
```

### From Qdrant (Semantic)

```python
# Semantically relevant memories
memories = qdrant.get_recent(project="git-steer", limit=5)

# Generates:
# ### Recent Activity
# - Fixed 9 security vulnerabilities
# - Updated to vitest 4.x
```

## Caching

Generated context is cached in Redis to avoid regeneration:

```python
# Cache TTL: 4 hours
cache.cache_context(project, context, ttl=3600 * 4)

# Invalidation triggers:
# - New memory added
# - Preference changed
# - Session ended
cache.invalidate_context(project)
```

## Configuration

### ContextInjector Setup

```python
from aiana.context import ContextInjector
from aiana.storage import AianaStorage
from aiana.storage.redis import RedisCache
from aiana.storage.qdrant import QdrantStorage
from aiana.embeddings import get_embedder

# Initialize backends
sqlite = AianaStorage()
redis = RedisCache()
embedder = get_embedder()
qdrant = QdrantStorage(embedder=embedder)

# Create injector
injector = ContextInjector(
    redis_cache=redis,
    qdrant_storage=qdrant,
    sqlite_storage=sqlite,
)
```

### Generating Context

```python
# Generate for a project
context = injector.generate_context(
    cwd="/Users/ryan/Projects/git-steer",
    session_id="abc123",
    max_items=10,
)

print(context)
# <aiana-context>
# ...
# </aiana-context>
```

## Hook Integration

### SessionStart Hook

```python
# In hooks.py or hook handler
def handle_session_start(session_id: str, cwd: str) -> dict:
    injector = ContextInjector(...)

    context = injector.generate_context(cwd, session_id)

    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }
```

### Claude Code Hook Config

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "aiana hook session-start"
      }]
    }]
  }
}
```

## Saving Session Summaries

When a session ends, save a summary for future context:

```python
# In session-end hook
injector.save_session_summary(
    session_id="abc123",
    project="git-steer",
    summary="Fixed 9 security vulnerabilities in dependencies"
)
```

This:
1. Adds to Qdrant for semantic retrieval
2. Updates dynamic context
3. Invalidates cached context

## Best Practices

### Preference Guidelines

**Good static preferences:**
- "Uses TypeScript for new projects"
- "Prefers ESLint flat config"
- "Uses conventional commit messages"

**Bad static preferences:**
- "Working on feature X" (too temporary)
- "Had a bug in auth" (too specific)

### Context Quality

Keep context concise and actionable:

```xml
<!-- Good -->
## User Preferences
- Uses uv for Python dependencies
- Prefers TypeScript

<!-- Bad (too verbose) -->
## User Preferences
- The user has indicated that they prefer to use the uv package manager
  for managing Python dependencies instead of pip because they find it
  faster and more reliable...
```

### Project Detection

The injector extracts project name from:

1. Git root directory name
2. Current directory name (fallback)

```python
def get_project_name(self, cwd: str) -> str:
    path = Path(cwd)
    # Try to find git root
    git_root = path
    while git_root != git_root.parent:
        if (git_root / ".git").exists():
            return git_root.name
        git_root = git_root.parent
    return path.name
```

## Debugging

### Check Cached Context

```python
context = redis.get_cached_context("git-steer")
if context:
    print("Cached context found")
else:
    print("No cached context")
```

### View Profile

```python
profile = redis.get_profile()
print(f"Static: {profile['static']}")
print(f"Dynamic: {profile['dynamic']}")
```

### Force Regeneration

```python
# Invalidate cache
redis.invalidate_context("git-steer")

# Regenerate
context = injector.generate_context(cwd, max_items=10)
```

## Empty Context

When no memories exist:

```xml
<aiana-context>
No previous context found for project: new-project
Memories will be saved as you work.
</aiana-context>
```

This informs Claude that:
1. This is a new/unknown project
2. Context will build over time
3. No assumptions should be made
