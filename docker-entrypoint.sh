#!/bin/bash
set -e

# Aiana Docker Entrypoint Script

# Display banner
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                        Aiana                              ║"
echo "║        AI Conversation Attendant for Claude Code          ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Check if Claude directory is mounted
if [ ! -d "/home/aiana/.claude/projects" ]; then
    echo "⚠️  Warning: Claude Code directory not mounted"
    echo "   Mount your ~/.claude directory to /home/aiana/.claude"
    echo "   Example: -v ~/.claude:/home/aiana/.claude:ro"
    echo ""
fi

# Initialize config if not present
if [ ! -f "/home/aiana/.aiana/config.yaml" ]; then
    echo "📝 Creating default configuration..."
    mkdir -p /home/aiana/.aiana
    cat > /home/aiana/.aiana/config.yaml << EOF
storage:
  type: sqlite
  path: /home/aiana/.aiana/conversations.db

recording:
  include_tool_results: true
  include_thinking: false
  redact_secrets: true

retention:
  days: 90
  max_sessions: 1000

privacy:
  encrypt_at_rest: false
EOF
fi

# Show status
echo "📊 Current Status:"
aiana status 2>/dev/null || echo "   No data yet"
echo ""

# Handle different commands
case "$1" in
    start)
        echo "🚀 Starting Aiana monitoring..."
        shift
        exec aiana start "$@"
        ;;
    watch)
        echo "👀 Starting file watcher..."
        exec aiana start --scan
        ;;
    list)
        shift
        exec aiana list "$@"
        ;;
    show)
        shift
        exec aiana show "$@"
        ;;
    search)
        shift
        exec aiana search "$@"
        ;;
    export)
        shift
        exec aiana export "$@"
        ;;
    status)
        exec aiana status
        ;;
    shell)
        exec /bin/bash
        ;;
    *)
        # Pass through to aiana CLI
        exec aiana "$@"
        ;;
esac
