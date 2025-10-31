# Aiana

**AI Conversation Attendant for Claude Code**

Aiana is a conversation monitoring and recording system that integrates with Claude Code to capture and store conversations in real-time.

## Overview

When you launch Claude Code, Aiana can optionally "listen in" to your conversation, recording the exchange for later review, analysis, or archival purposes.

## Features (Planned)

- **Real-time Monitoring**: Captures conversations as they happen via Claude Code API
- **User Opt-in**: Prompts for permission when Claude Code launches
- **Secure Storage**: Conversations stored locally with privacy in mind
- **Conversation Replay**: Review past conversations
- **Search & Filter**: Find specific topics or exchanges
- **Privacy First**: User controls what gets recorded and stored

## Status

🚧 **In Development** - This project is in active development as part of the commit-relay multi-agent system.

### Current Phase

- [x] Repository created
- [ ] API research (investigating Claude Code conversation access)
- [ ] Architecture design
- [ ] Implementation
- [ ] Testing
- [ ] Documentation

## Architecture

Aiana is designed to integrate with Claude Code through its API, enabling:

1. **Conversation Access**: Retrieval of conversation data in real-time
2. **Storage Layer**: Local conversation database
3. **User Interface**: Simple opt-in mechanism and conversation viewer
4. **Privacy Controls**: User-configurable retention and filtering

## Technical Stack

- **Language**: Python 3.10+
- **Integration**: Claude Code API
- **Storage**: TBD (based on requirements)
- **Framework**: TBD (potentially MCP server or CLI wrapper)

## Installation

*Coming soon*

## Usage

*Coming soon*

## Development

This project is managed by the commit-relay multi-agent system at [@ry-ops/commit-relay](https://github.com/ry-ops/commit-relay).

### Development Agents

- **Development Agent**: Feature implementation and bug fixes
- **Security Agent**: Security audits and vulnerability management
- **Coordinator Agent**: Task orchestration and planning

## Privacy & Security

Aiana is designed with privacy as a core principle:

- **Local Storage**: Conversations stored on your machine
- **No Cloud Sync**: Data stays local unless you explicitly export it
- **User Control**: Complete control over what gets recorded
- **Encryption**: *Planned* - Conversation encryption at rest

## Contributing

This is a personal project under active development. Contributions and suggestions welcome via issues.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Roadmap

- [ ] Phase 1: API Research & Architecture
- [ ] Phase 2: Core Implementation
- [ ] Phase 3: User Interface
- [ ] Phase 4: Advanced Features (search, export, analytics)

---

**Project**: Part of the [@ry-ops](https://github.com/ry-ops) ecosystem
**Status**: 🚧 Active Development
**Created**: 2025-10-31
