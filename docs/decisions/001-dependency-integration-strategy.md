# ADR-001: Third-Party Dependency Integration Strategy

**Date:** 2026-02-04
**Status:** Accepted
**Context:** Mem0 integration into AIANA

## Decision

When integrating third-party libraries that provide core functionality, use the **Pinned Dependency with Wrapper Pattern**:

1. **Pin to major version** - Allow patches, block breaking changes
   ```toml
   "mem0ai>=1.0.3,<2.0"  # Not ">=0.1.0"
   ```

2. **Create a wrapper class** - Isolate the third-party API
   ```python
   class Mem0Storage:
       """Wraps mem0ai, matching our internal interface."""
       def add_memory(...) -> str
       def search(...) -> list[dict]
   ```

3. **Maintain a fallback** - Keep alternative implementation working
   ```python
   # If Mem0 fails, fall back to QdrantStorage
   if self.mem0 is None:
       self.qdrant = QdrantStorage(...)
   ```

## Rationale

### Why Not Direct Loose Dependency (`>=0.1.0`)
- Breaking changes propagate immediately
- No protection against API changes
- Debugging becomes harder ("it worked yesterday")

### Why Not Fork
- Maintenance burden (security patches, updates)
- Miss community improvements (249+ contributors on Mem0)
- Overkill unless project is unmaintained or needs deep customization

### Why Wrapper Pattern Works
- **Isolation**: Third-party API changes stay in one file
- **Testability**: Can mock the wrapper for testing
- **Swappability**: Can replace Mem0 with alternative without touching callers
- **Graceful degradation**: Fallback to simpler implementation

## Checklist for Future Integrations

Before adding a third-party dependency:

- [ ] Check project health (stars, contributors, release frequency)
- [ ] Review license compatibility (prefer MIT, Apache 2.0)
- [ ] Check for recent major version (API stability)
- [ ] Pin version to `>=current,<next_major`
- [ ] Create wrapper class matching internal interface
- [ ] Implement fallback if dependency is optional
- [ ] Add to this document if it's a significant integration

## Applied To

| Dependency | Version Constraint | Wrapper | Fallback |
|------------|-------------------|---------|----------|
| mem0ai | `>=1.0.3,<2.0` | `Mem0Storage` | `QdrantStorage` |
| qdrant-client | `>=1.7.0` | `QdrantStorage` | SQLite FTS |
| redis | `>=5.0.0` | `RedisCache` | In-memory |
| mcp | `>=1.0.0` | Native | CLI mode |

## References

- Mem0 GitHub: https://github.com/mem0ai/mem0 (46.6k stars, Apache 2.0)
- Semantic Versioning: https://semver.org/
- Python Dependency Specification: https://peps.python.org/pep-0440/
