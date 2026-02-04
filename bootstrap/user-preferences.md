# AIANA Bootstrap: User Preferences

These preferences should be loaded into AIANA's memory on first run.

## Development Standards

### Package Management
- Use **uv** for Python projects (fast, reliable)
- Use **pnpm** or **npm** for Node.js projects
- Always include lockfiles (uv.lock, package-lock.json)

### Dependencies
- **Wrapper pattern** for third-party integrations
- **Pin to major version**: `>=x.y.z,<next_major`
- Maintain fallback implementations when possible
- Document integration decisions in ADR files

### Infrastructure Stack (When Available)
- **Qdrant** for vector storage/semantic search
- **Redis** for caching, session state, preferences
- **SQLite** for local persistent storage
- **Docker Compose** for local development stack

### Repository Setup
- Proper **README.md** with:
  - Project description
  - Architecture section with diagram
  - Quick start / installation
  - Configuration options
  - Changelog
- **Animated SVG** architecture diagram (GitHub-compatible)
- **Semantic versioning** (semver)
- **ADR documents** for significant decisions (`docs/decisions/`)
- **CLAUDE.md** for Claude Code context

### Code Standards
- TypeScript strict mode for TS projects
- Type hints for Python
- ESLint/Ruff for linting
- Tests with good coverage

### Git Practices
- Conventional commits
- Feature branches
- PR descriptions with context
- Don't commit secrets

## Project Checklist

When starting a new project or updating existing:

- [ ] pyproject.toml / package.json with proper metadata
- [ ] README.md with architecture section
- [ ] Animated SVG diagram
- [ ] Version number set appropriately
- [ ] Lockfile committed
- [ ] Docker Compose if using Qdrant/Redis
- [ ] CLAUDE.md for AI context
- [ ] ADR folder for decisions
- [ ] CI/CD workflow (if applicable)

## Memory Types

When AIANA captures memories, classify as:
- **preference** - Long-term user standards (this file)
- **pattern** - Recurring solutions/approaches
- **decision** - Specific architectural choices
- **insight** - Learned optimizations
