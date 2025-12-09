# TOS Compatibility Analysis for Aiana

This document analyzes whether Aiana (AI Conversation Attendant) is compatible with Anthropic's Terms of Service and Usage Policies.

## Executive Summary

**Verdict: CONDITIONALLY COMPATIBLE**

Aiana's core functionality of recording Claude Code conversations locally is **likely permissible** under Anthropic's current policies, with important caveats and best practices to follow.

## Relevant Policy Documents

1. **Anthropic Usage Policy** (formerly Acceptable Use Policy)
2. **Commercial Terms of Service** (API/Console)
3. **Consumer Terms of Service** (Claude.ai, Claude Pro/Max)
4. **Privacy Policy**
5. **Claude Code Data Usage Documentation**

## Key Policy Analysis

### 1. Data Ownership & Storage Rights

**Policy Position**:
> "Subject to Customer's compliance with these Terms, Anthropic assigns to Customer its right, title and interest (if any) in and to Outputs."

**Analysis**: Users own their conversation outputs. Storing these locally is explicitly permitted.

**Aiana Compliance**: **COMPLIANT**
- Users own their conversations
- Local storage respects this ownership
- No data leaves user's machine without consent

### 2. Recording/Logging Conversations

**Policy Position**:
The Usage Policy does not prohibit users from recording their own conversations with Claude. The restriction is on:
> "Gathering information on an individual or group in order to track, target, or report on their identity"

**Analysis**: Self-recording for personal use, productivity, or compliance purposes is not prohibited.

**Aiana Compliance**: **COMPLIANT** (with conditions)
- Recording YOUR OWN conversations: Permitted
- Recording OTHER USERS' conversations without consent: Prohibited
- Team/enterprise use requires proper consent mechanisms

### 3. Third-Party Tool Development

**Policy Position**:
Anthropic actively encourages ecosystem development through:
- MCP (Model Context Protocol) - open source
- Hooks system for Claude Code
- Plugin architecture (public beta)
- API access for developers

**Analysis**: Building tools that integrate with Claude Code is explicitly supported.

**Aiana Compliance**: **COMPLIANT**
- Uses official hooks API
- Reads local files (user's own data)
- Does not circumvent any restrictions

### 4. Privacy & Data Processing

**Policy Position**:
> "Only files that Claude Code explicitly reads are sent to servers... Your local environment, installed packages, and system configuration stay local."

**Analysis**: Local data processing is the expected model.

**Aiana Compliance**: **COMPLIANT**
- All processing happens locally
- No data sent to external servers
- User controls all data retention

### 5. Model Training Restrictions

**Policy Position**:
> "Anthropic may not train models on Customer Content from Services" (Commercial)

**Analysis**: This restricts Anthropic, not users. Users can use their data as they wish.

**Aiana Compliance**: **NOT APPLICABLE**
- Aiana doesn't train models
- User data stays with user

## Potential Risk Areas

### Risk 1: Team/Enterprise Multi-User Recording

**Concern**: Recording conversations of team members without explicit consent.

**Mitigation**:
- Require explicit opt-in per user
- Clear disclosure that conversations are being recorded
- Team admins must configure, individual users must consent

**Risk Level**: MEDIUM (manageable with proper UX)

### Risk 2: Sensitive Data in Conversations

**Concern**: Conversations may contain secrets, credentials, PII.

**Mitigation**:
- Implement secret scanning/redaction
- Warn users about sensitive content
- Provide selective recording (exclude certain sessions)
- Encryption at rest

**Risk Level**: MEDIUM (best practices needed)

### Risk 3: Redistribution of Conversations

**Concern**: Users might share/publish conversation data inappropriately.

**Mitigation**:
- This is a user responsibility, not Aiana's
- Document best practices
- Don't build "easy share" features that encourage risky behavior

**Risk Level**: LOW (user responsibility)

### Risk 4: Circumventing Rate Limits/Restrictions

**Concern**: Could Aiana be seen as helping users bypass restrictions?

**Analysis**: No. Aiana only records what already happened.

**Risk Level**: NONE

## Compliance Checklist

### Required for TOS Compliance

- [x] Local-only data storage (no external transmission)
- [x] User-initiated recording (opt-in)
- [x] Uses official APIs/hooks (no reverse engineering)
- [x] Respects user data ownership
- [x] No model training on conversation data
- [ ] Clear privacy disclosure in README/docs
- [ ] User consent mechanism before recording
- [ ] Data retention controls

### Recommended Best Practices

- [ ] Encrypt conversations at rest
- [ ] Implement secret scanning
- [ ] Provide selective recording controls
- [ ] Document data handling clearly
- [ ] Support data export in standard formats
- [ ] Implement data deletion functionality
- [ ] Team consent mechanisms for enterprise

## Similar Approved Projects

The following community projects operate in similar space without TOS issues:

1. **ccusage** - Reads Claude Code log files for cost tracking
2. **claude-code-log** - Converts JSONL transcripts to HTML
3. **claude-history** - Extracts conversation history from session files
4. **claude-JSONL-browser** - Web viewer for conversation logs

These projects demonstrate that:
- Reading local Claude Code files is accepted
- Converting/displaying conversation data is permitted
- Community tooling around Claude Code is encouraged

## Legal Disclaimer

This analysis is not legal advice. It represents a good-faith interpretation of publicly available policies as of December 2025. Users should:

1. Review current Anthropic policies before deployment
2. Consult legal counsel for enterprise deployments
3. Monitor policy updates that may affect compliance

## Recommendations for Aiana Development

### Phase 1: MVP (Low Risk)
- Personal use only
- Local storage
- Explicit opt-in
- Read-only access to existing files

### Phase 2: Enhanced (Medium Risk)
- Team support with consent mechanisms
- Secret scanning/redaction
- Encryption at rest
- Selective recording

### Phase 3: Enterprise (Requires Review)
- Centralized storage options
- Compliance reporting
- Audit logging
- Legal review recommended

## Conclusion

Aiana is **compatible with Anthropic's TOS** for the following reasons:

1. **Users own their data** - Recording your own conversations is permitted
2. **Local processing** - No external data transmission
3. **Official APIs** - Uses hooks system and file access
4. **Privacy-first** - Aligns with Anthropic's privacy principles
5. **Ecosystem encouraged** - Anthropic actively promotes developer tools

**Proceed with development**, implementing the compliance checklist and best practices above.

---

*Analysis Date: December 2025*
*Policy Version: Usage Policy (June 2024 update)*
*Analyst: Cortex Multi-Agent System*
