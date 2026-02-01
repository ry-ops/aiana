# MCP Server

Aiana can run as an MCP (Model Context Protocol) server, exposing memory operations directly to Claude Code and other MCP clients.

## Overview

```
┌─────────────────┐         ┌─────────────────┐
│  Claude Code    │  MCP    │     Aiana       │
│                 │ ◄─────► │   MCP Server    │
│  "Search my     │         │                 │
│   memories"     │         │  ┌───────────┐  │
└─────────────────┘         │  │  SQLite   │  │
                            │  │  Redis    │  │
                            │  │  Qdrant   │  │
                            │  └───────────┘  │
                            └─────────────────┘
```

## Starting the Server

### CLI

```bash
# Start MCP server (stdio mode)
aiana mcp
```

### Programmatic

```python
from aiana.mcp.server import AianaMCPServer
import asyncio

server = AianaMCPServer()
asyncio.run(server.run())
```

### Docker

```bash
docker compose exec aiana aiana mcp
```

---

## Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

Or for Docker:

```json
{
  "mcpServers": {
    "aiana": {
      "command": "docker",
      "args": ["compose", "exec", "-T", "aiana", "aiana", "mcp"]
    }
  }
}
```

Restart Claude Desktop after configuration changes.

---

## Available Tools

### memory_search

Search through past conversations and memories semantically.

**Input Schema:**
```json
{
  "query": "string (required)",
  "project": "string (optional)",
  "limit": "integer (default: 10)"
}
```

**Example:**
```
User: "Search for how I fixed the authentication bug"

Claude: [calls memory_search with query="authentication bug fix"]

Result:
{
  "query": "authentication bug fix",
  "count": 3,
  "results": [
    {
      "source": "semantic",
      "score": 0.89,
      "content": "Fixed JWT validation by adding expiry check...",
      "project": "cortex",
      "timestamp": "2026-01-15T10:30:00Z"
    }
  ]
}
```

---

### memory_add

Save a memory or note for future recall.

**Input Schema:**
```json
{
  "content": "string (required)",
  "memory_type": "note|preference|pattern|insight (default: note)",
  "project": "string (optional)"
}
```

**Example:**
```
User: "Remember that cortex uses uv for Python dependencies"

Claude: [calls memory_add with content="cortex uses uv for Python dependencies", type="pattern"]

Result:
{
  "status": "saved",
  "memory_id": "abc123",
  "type": "pattern",
  "project": null
}
```

---

### memory_recall

Recall context for a specific project.

**Input Schema:**
```json
{
  "project": "string (required)",
  "max_items": "integer (default: 5)"
}
```

**Example:**
```
User: "What do you remember about git-steer?"

Claude: [calls memory_recall with project="git-steer"]

Result:
{
  "project": "git-steer",
  "context": "<aiana-context>\n## Project: git-steer\n- TypeScript MCP server\n- Uses GitHub Actions for security fixes\n- Recently added blog post series\n</aiana-context>"
}
```

---

### session_list

List recorded conversation sessions.

**Input Schema:**
```json
{
  "project": "string (optional)",
  "limit": "integer (default: 20)"
}
```

**Example:**
```
User: "Show my recent sessions"

Claude: [calls session_list]

Result:
{
  "count": 5,
  "sessions": [
    {
      "id": "abc12345",
      "project": "/Users/ryan/Projects/git-steer",
      "started": "2026-02-01T10:00:00Z",
      "messages": 47,
      "tokens": 12500,
      "active": false
    }
  ]
}
```

---

### session_show

View details of a specific session.

**Input Schema:**
```json
{
  "session_id": "string (required, can be partial)",
  "limit": "integer (optional, limits messages)"
}
```

**Example:**
```
User: "Show session abc123"

Claude: [calls session_show with session_id="abc123"]

Result:
{
  "session": {
    "id": "abc12345-full-id",
    "project": "/Users/ryan/Projects/git-steer",
    "started": "2026-02-01T10:00:00Z",
    "messages": 47
  },
  "messages": [
    {
      "type": "user",
      "content": "Fix security vulnerabilities...",
      "timestamp": "2026-02-01T10:00:00Z"
    }
  ]
}
```

---

### preference_add

Add a user preference for future context injection.

**Input Schema:**
```json
{
  "preference": "string (required)",
  "permanent": "boolean (default: true)"
}
```

**Example:**
```
User: "Remember that I prefer TypeScript over JavaScript"

Claude: [calls preference_add with preference="Prefers TypeScript over JavaScript"]

Result:
{
  "status": "saved",
  "preference": "Prefers TypeScript over JavaScript",
  "permanent": true
}
```

---

### aiana_status

Get system health and statistics.

**Input Schema:**
```json
{}
```

**Example:**
```
User: "Check Aiana status"

Claude: [calls aiana_status]

Result:
{
  "aiana": "running",
  "backends": {
    "sqlite": {
      "status": "connected",
      "sessions": 150,
      "messages": 4200
    },
    "redis": {
      "status": "connected",
      "used_memory": "2.5M",
      "active_sessions": 1
    },
    "qdrant": {
      "status": "connected",
      "total_memories": 890,
      "indexed_vectors": 890
    }
  }
}
```

---

## Error Handling

Tools return errors in a consistent format:

```json
{
  "error": "Error message here"
}
```

Common errors:

| Error | Cause |
|-------|-------|
| `SQLite storage not available` | Database not initialized |
| `Embedder required` | Qdrant search without embedder |
| `Session not found: {id}` | Invalid session ID |
| `Context injector not available` | Missing dependencies |

---

## Backend Initialization

The MCP server lazily initializes backends on first tool call:

1. **SQLite** - Always available (required)
2. **Redis** - Optional, enables caching
3. **Qdrant** - Optional, enables semantic search
4. **Embedder** - Required for Qdrant

Missing backends degrade gracefully:
- No Redis → No context caching
- No Qdrant → Falls back to FTS search

---

## Development

### Testing Tools

```bash
# Start server in debug mode
AIANA_DEBUG=true aiana mcp
```

### Custom Tools

Extend `AianaMCPServer` to add custom tools:

```python
from aiana.mcp.server import AianaMCPServer

class CustomMCPServer(AianaMCPServer):
    def _setup_handlers(self):
        super()._setup_handlers()

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            if name == "my_custom_tool":
                return await self._my_custom_tool(arguments)
            return await super().call_tool(name, arguments)

    async def _my_custom_tool(self, args: dict) -> dict:
        # Custom implementation
        return {"result": "success"}
```

---

## Integration with git-steer

When both Aiana and git-steer are configured as MCP servers:

```json
{
  "mcpServers": {
    "aiana": {
      "command": "aiana",
      "args": ["mcp"]
    },
    "git-steer": {
      "command": "npx",
      "args": ["git-steer"]
    }
  }
}
```

Claude can then:
1. Use git-steer to fix security vulnerabilities
2. Use Aiana to remember the fix pattern
3. Recall the pattern for future similar tasks

```
User: "Fix security vulnerabilities in cortex"

Claude:
1. [Aiana memory_recall] - Check for past patterns
2. [git-steer security_scan] - Find vulnerabilities
3. [git-steer security_fix_pr] - Create fix PR
4. [Aiana memory_add] - Save the pattern for future
```
