"""Command-line interface for Aiana."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from aiana import __version__
from aiana.config import get_aiana_dir, load_config, save_config
from aiana.hooks import HookHandler, install_hooks, uninstall_hooks
from aiana.models import Message, MessageType
from aiana.storage import AianaStorage
from aiana.watcher import TranscriptWatcher, WatcherDaemon

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="aiana")
def main():
    """Aiana - AI Conversation Attendant for Claude Code.

    Monitor and record Claude Code conversations locally.
    """
    pass


# ============================================================================
# Session Management
# ============================================================================


@main.command()
@click.option("-p", "--project", help="Filter by project path")
@click.option("-l", "--limit", default=20, help="Number of sessions to show")
@click.option("-f", "--format", "fmt", type=click.Choice(["table", "json"]), default="table")
def list(project: Optional[str], limit: int, fmt: str):
    """List recorded sessions."""
    storage = AianaStorage()
    sessions = storage.list_sessions(project=project, limit=limit)

    if not sessions:
        console.print("[dim]No sessions found.[/dim]")
        return

    if fmt == "json":
        data = [
            {
                "id": s.id,
                "project": s.project_path,
                "started_at": s.started_at.isoformat(),
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "messages": s.message_count,
                "tokens": s.token_count,
            }
            for s in sessions
        ]
        console.print_json(json.dumps(data, indent=2))
        return

    table = Table(title="Recorded Sessions")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Project", style="green")
    table.add_column("Started", style="yellow")
    table.add_column("Messages", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Status")

    for session in sessions:
        status = "[green]Active[/green]" if session.is_active else "[dim]Ended[/dim]"
        started = session.started_at.strftime("%Y-%m-%d %H:%M")
        project_display = Path(session.project_path).name or session.project_path

        table.add_row(
            session.id[:8],
            project_display[:30],
            started,
            str(session.message_count),
            str(session.token_count),
            status,
        )

    console.print(table)


@main.command()
@click.argument("session_id")
@click.option("-f", "--format", "fmt", type=click.Choice(["text", "json", "markdown"]), default="text")
@click.option("-l", "--limit", type=int, help="Limit number of messages")
def show(session_id: str, fmt: str, limit: Optional[int]):
    """Display a session transcript."""
    storage = AianaStorage()

    # Find session by prefix
    sessions = storage.list_sessions(limit=100)
    session = None
    for s in sessions:
        if s.id.startswith(session_id):
            session = s
            break

    if not session:
        console.print(f"[red]Session not found: {session_id}[/red]")
        return

    messages = storage.get_messages(session.id, limit=limit)

    if fmt == "json":
        data = {
            "session": {
                "id": session.id,
                "project": session.project_path,
                "started_at": session.started_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            },
            "messages": [
                {
                    "type": m.type.value,
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "tool": m.tool_name,
                }
                for m in messages
            ],
        }
        console.print_json(json.dumps(data, indent=2))
        return

    if fmt == "markdown":
        print(f"# Session {session.id[:8]}")
        print(f"\n**Project**: {session.project_path}")
        print(f"**Started**: {session.started_at}")
        print(f"**Messages**: {session.message_count}")
        print("\n---\n")

        for msg in messages:
            if msg.type == MessageType.USER:
                print(f"## User\n\n{msg.content}\n")
            elif msg.type == MessageType.ASSISTANT:
                print(f"## Assistant\n\n{msg.content}\n")
            elif msg.type == MessageType.TOOL_USE:
                print(f"## Tool: {msg.tool_name}\n\n```\n{msg.content[:500]}\n```\n")
        return

    # Text format
    console.print(Panel(
        f"[bold]Session[/bold]: {session.id}\n"
        f"[bold]Project[/bold]: {session.project_path}\n"
        f"[bold]Started[/bold]: {session.started_at}\n"
        f"[bold]Messages[/bold]: {session.message_count}",
        title="Session Info",
    ))
    console.print()

    for msg in messages:
        if msg.type == MessageType.USER:
            console.print(Panel(
                msg.content,
                title="[cyan]User[/cyan]",
                border_style="cyan",
            ))
        elif msg.type == MessageType.ASSISTANT:
            console.print(Panel(
                msg.content[:2000] + ("..." if len(msg.content) > 2000 else ""),
                title="[green]Assistant[/green]",
                border_style="green",
            ))
        elif msg.type == MessageType.TOOL_USE:
            console.print(Panel(
                f"[dim]{msg.content[:500]}...[/dim]" if msg.content else "[dim]No output[/dim]",
                title=f"[yellow]Tool: {msg.tool_name}[/yellow]",
                border_style="yellow",
            ))
        console.print()


@main.command()
@click.argument("query")
@click.option("-p", "--project", help="Filter by project path")
@click.option("-l", "--limit", default=20, help="Maximum results")
def search(query: str, project: Optional[str], limit: int):
    """Search across conversations."""
    storage = AianaStorage()
    messages = storage.search(query, project=project, limit=limit)

    if not messages:
        console.print(f"[dim]No results for: {query}[/dim]")
        return

    console.print(f"[bold]Found {len(messages)} results for:[/bold] {query}\n")

    for msg in messages:
        # Highlight matching content
        content = msg.content[:200]
        if query.lower() in content.lower():
            content = content.replace(query, f"[bold yellow]{query}[/bold yellow]")

        role_color = "cyan" if msg.type == MessageType.USER else "green"
        console.print(f"[{role_color}]{msg.type.value}[/{role_color}] ({msg.session_id[:8]})")
        console.print(f"  {content}...")
        console.print()


@main.command()
@click.argument("session_id")
@click.option("-f", "--format", "fmt", type=click.Choice(["json", "markdown"]), default="markdown")
@click.option("-o", "--output", type=click.Path(), help="Output file path")
def export(session_id: str, fmt: str, output: Optional[str]):
    """Export a session to file."""
    storage = AianaStorage()

    # Find session
    sessions = storage.list_sessions(limit=100)
    session = None
    for s in sessions:
        if s.id.startswith(session_id):
            session = s
            break

    if not session:
        console.print(f"[red]Session not found: {session_id}[/red]")
        return

    messages = storage.get_messages(session.id)

    if fmt == "json":
        data = {
            "session": {
                "id": session.id,
                "project": session.project_path,
                "started_at": session.started_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "message_count": session.message_count,
                "token_count": session.token_count,
            },
            "messages": [
                {
                    "id": m.id,
                    "type": m.type.value,
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "tool_name": m.tool_name,
                }
                for m in messages
            ],
        }
        content = json.dumps(data, indent=2)
    else:
        lines = [
            f"# Session {session.id[:8]}",
            "",
            f"**Project**: {session.project_path}",
            f"**Started**: {session.started_at}",
            f"**Ended**: {session.ended_at or 'Active'}",
            f"**Messages**: {session.message_count}",
            f"**Tokens**: {session.token_count}",
            "",
            "---",
            "",
        ]

        for msg in messages:
            ts = msg.timestamp.strftime("%H:%M:%S")
            if msg.type == MessageType.USER:
                lines.extend([f"## [{ts}] User", "", msg.content, ""])
            elif msg.type == MessageType.ASSISTANT:
                lines.extend([f"## [{ts}] Assistant", "", msg.content, ""])
            elif msg.type in (MessageType.TOOL_USE, MessageType.TOOL_RESULT):
                lines.extend([
                    f"### [{ts}] Tool: {msg.tool_name}",
                    "",
                    "```",
                    msg.content[:1000],
                    "```",
                    "",
                ])

        content = "\n".join(lines)

    if output:
        Path(output).write_text(content)
        console.print(f"[green]Exported to {output}[/green]")
    else:
        print(content)


# ============================================================================
# Monitoring
# ============================================================================


@main.command()
@click.option("-d", "--daemon", is_flag=True, help="Run in background")
@click.option("--scan", is_flag=True, help="Scan existing transcripts first")
def start(daemon: bool, scan: bool):
    """Start monitoring Claude Code sessions."""
    console.print("[bold]Starting Aiana...[/bold]")

    watcher = TranscriptWatcher(
        on_message=lambda m: console.print(f"[dim]Recorded: {m.type.value}[/dim]")
    )

    if scan:
        console.print("Scanning existing transcripts...")
        count = watcher.scan_existing()
        console.print(f"[green]Imported {count} transcript files[/green]")

    watcher.start()
    console.print("[green]Monitoring started[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
        console.print("\n[yellow]Monitoring stopped[/yellow]")


@main.command()
def status():
    """Show monitoring status and statistics."""
    storage = AianaStorage()
    stats = storage.get_stats()
    config = load_config()

    # SQLite stats
    console.print(Panel(
        f"[bold]Sessions[/bold]: {stats['sessions']}\n"
        f"[bold]Messages[/bold]: {stats['messages']}\n"
        f"[bold]Total Tokens[/bold]: {stats['total_tokens']:,}\n"
        f"[bold]Database Size[/bold]: {stats['db_size_bytes'] / 1024:.1f} KB",
        title="SQLite Storage",
    ))

    # Redis stats
    try:
        from aiana.storage.redis import RedisCache
        redis = RedisCache()
        redis_stats = redis.get_stats()
        status_icon = "[green]Connected[/green]" if redis_stats.get("connected") else "[red]Disconnected[/red]"
        console.print(Panel(
            f"[bold]Status[/bold]: {status_icon}\n"
            f"[bold]Memory Used[/bold]: {redis_stats.get('used_memory', 'N/A')}\n"
            f"[bold]Active Sessions[/bold]: {redis_stats.get('active_sessions', 0)}",
            title="Redis Cache",
        ))
    except Exception:
        console.print(Panel(
            "[dim]Not configured or not running[/dim]",
            title="Redis Cache",
        ))

    # Qdrant stats
    try:
        from aiana.storage.qdrant import QdrantStorage
        from aiana.embeddings import get_embedder
        embedder = get_embedder()
        qdrant = QdrantStorage(embedder=embedder)
        qdrant_stats = qdrant.get_stats()
        console.print(Panel(
            f"[bold]Status[/bold]: [green]{qdrant_stats.get('status', 'unknown')}[/green]\n"
            f"[bold]Total Memories[/bold]: {qdrant_stats.get('total_memories', 0)}\n"
            f"[bold]Indexed Vectors[/bold]: {qdrant_stats.get('indexed_vectors', 0)}",
            title="Qdrant Vector Store",
        ))
    except Exception:
        console.print(Panel(
            "[dim]Not configured or not running[/dim]",
            title="Qdrant Vector Store",
        ))

    # Configuration
    console.print(Panel(
        f"[bold]Storage Path[/bold]: {config.storage.path}\n"
        f"[bold]Retention[/bold]: {config.retention.days} days\n"
        f"[bold]Secret Redaction[/bold]: {'Enabled' if config.recording.redact_secrets else 'Disabled'}",
        title="Configuration",
    ))


# ============================================================================
# Hook Commands (Internal)
# ============================================================================


@main.group()
def hook():
    """Handle Claude Code hook events (internal use)."""
    pass


@hook.command("session-start")
def hook_session_start():
    """Handle SessionStart hook event."""
    handler = HookHandler()
    result = handler.handle_stdin()
    if result:
        print(json.dumps(result))


@hook.command("session-end")
def hook_session_end():
    """Handle SessionEnd hook event."""
    handler = HookHandler()
    result = handler.handle_stdin()
    if result:
        print(json.dumps(result))


@hook.command("post-tool")
def hook_post_tool():
    """Handle PostToolUse hook event."""
    handler = HookHandler()
    result = handler.handle_stdin()
    if result:
        print(json.dumps(result))


# ============================================================================
# Installation
# ============================================================================


@main.command()
@click.option("--force", is_flag=True, help="Force reinstall hooks")
def install(force: bool):
    """Install Aiana hooks into Claude Code."""
    console.print("[bold]Installing Aiana hooks...[/bold]")

    if install_hooks(force=force):
        console.print("[green]Hooks installed successfully![/green]")
        console.print("\nRestart Claude Code for hooks to take effect.")
    else:
        console.print("[yellow]Hooks already installed. Use --force to reinstall.[/yellow]")


@main.command()
def uninstall():
    """Remove Aiana hooks from Claude Code."""
    console.print("[bold]Removing Aiana hooks...[/bold]")

    if uninstall_hooks():
        console.print("[green]Hooks removed successfully![/green]")
    else:
        console.print("[yellow]No Aiana hooks found.[/yellow]")


# ============================================================================
# Configuration
# ============================================================================


@main.command()
@click.option("--show", is_flag=True, help="Show current configuration")
@click.option("--reset", is_flag=True, help="Reset to defaults")
def config(show: bool, reset: bool):
    """Configure Aiana settings."""
    from aiana.config import AianaConfig, get_config_path

    if reset:
        cfg = AianaConfig()
        save_config(cfg)
        console.print("[green]Configuration reset to defaults.[/green]")
        return

    if show:
        cfg = load_config()
        console.print_json(json.dumps(cfg.to_dict(), indent=2))
        return

    # Show config location
    config_path = get_config_path()
    console.print(f"Configuration file: {config_path}")
    console.print("\nUse --show to view current settings")
    console.print("Use --reset to restore defaults")
    console.print(f"\nEdit {config_path} directly to customize settings.")


# ============================================================================
# MCP Server
# ============================================================================


@main.command()
@click.option("--port", default=8765, help="Port for MCP server (default 8765)")
def mcp(port: int):
    """Start Aiana as an MCP server."""
    try:
        from aiana.mcp.server import AianaMCPServer
        import asyncio

        console.print("[bold]Starting Aiana MCP Server...[/bold]")
        console.print(f"[dim]Exposing memory tools via MCP protocol[/dim]")

        server = AianaMCPServer()
        asyncio.run(server.run())

    except ImportError as e:
        console.print(f"[red]MCP not available: {e}[/red]")
        console.print("Install with: pip install aiana[mcp]")
    except KeyboardInterrupt:
        console.print("\n[yellow]MCP server stopped[/yellow]")


# ============================================================================
# Memory Commands
# ============================================================================


@main.group()
def memory():
    """Manage Aiana memories."""
    pass


@memory.command("search")
@click.argument("query")
@click.option("-p", "--project", help="Filter by project")
@click.option("-l", "--limit", default=10, help="Maximum results")
def memory_search(query: str, project: Optional[str], limit: int):
    """Search memories semantically."""
    try:
        from aiana.storage.qdrant import QdrantStorage
        from aiana.embeddings import get_embedder

        embedder = get_embedder()
        storage = QdrantStorage(embedder=embedder)

        results = storage.search(query=query, project=project, limit=limit)

        if not results:
            console.print(f"[dim]No results for: {query}[/dim]")
            return

        console.print(f"[bold]Found {len(results)} results for:[/bold] {query}\n")

        for r in results:
            score = int(r["score"] * 100)
            content = r["content"][:200]
            console.print(f"[cyan]{score}% match[/cyan]")
            console.print(f"  {content}...")
            if r.get("project"):
                console.print(f"  [dim]Project: {r['project']}[/dim]")
            console.print()

    except ImportError:
        console.print("[red]Vector search not available.[/red]")
        console.print("Install with: pip install aiana[vector]")

        # Fallback to SQLite FTS
        console.print("\n[dim]Falling back to full-text search...[/dim]\n")
        storage = AianaStorage()
        messages = storage.search(query, project=project, limit=limit)

        if not messages:
            console.print(f"[dim]No results for: {query}[/dim]")
            return

        for m in messages:
            console.print(f"[cyan]{m.type.value}[/cyan] ({m.session_id[:8]})")
            console.print(f"  {m.content[:200]}...")
            console.print()


@memory.command("add")
@click.argument("content")
@click.option("-t", "--type", "memory_type", default="note",
              type=click.Choice(["note", "preference", "pattern", "insight"]))
@click.option("-p", "--project", help="Associated project")
def memory_add(content: str, memory_type: str, project: Optional[str]):
    """Add a memory manually."""
    try:
        from aiana.storage.qdrant import QdrantStorage
        from aiana.embeddings import get_embedder

        embedder = get_embedder()
        storage = QdrantStorage(embedder=embedder)

        memory_id = storage.add_memory(
            content=content,
            session_id="manual",
            project=project,
            memory_type=memory_type,
        )

        console.print(f"[green]Memory saved![/green]")
        console.print(f"ID: {memory_id}")
        console.print(f"Type: {memory_type}")
        if project:
            console.print(f"Project: {project}")

    except ImportError:
        console.print("[red]Vector storage not available.[/red]")
        console.print("Install with: pip install aiana[vector]")


@memory.command("recall")
@click.argument("project")
@click.option("-m", "--max-items", default=5, help="Max items per section")
def memory_recall(project: str, max_items: int):
    """Recall context for a project."""
    try:
        from aiana.context import ContextInjector
        from aiana.storage.redis import RedisCache
        from aiana.storage.qdrant import QdrantStorage
        from aiana.embeddings import get_embedder

        embedder = get_embedder()
        qdrant = QdrantStorage(embedder=embedder)
        redis = RedisCache()
        sqlite = AianaStorage()

        injector = ContextInjector(
            redis_cache=redis,
            qdrant_storage=qdrant,
            sqlite_storage=sqlite,
        )

        context = injector.generate_context(
            cwd=f"/projects/{project}",
            max_items=max_items,
        )

        console.print(Panel(context, title=f"Context for {project}"))

    except ImportError as e:
        console.print(f"[red]Context injection not available: {e}[/red]")
        console.print("Install with: pip install aiana[all]")


# ============================================================================
# Preference Commands
# ============================================================================


@main.command()
@click.argument("preference")
@click.option("--temporary", is_flag=True, help="Make preference temporary (dynamic)")
def prefer(preference: str, temporary: bool):
    """Add a user preference."""
    try:
        from aiana.storage.redis import RedisCache

        cache = RedisCache()
        cache.add_preference(preference, static=not temporary)

        pref_type = "temporary" if temporary else "permanent"
        console.print(f"[green]Preference saved ({pref_type})![/green]")
        console.print(f"  {preference}")

    except ImportError:
        console.print("[red]Redis not available.[/red]")
        console.print("Preferences require Redis. Start with docker-compose.")


if __name__ == "__main__":
    main()
