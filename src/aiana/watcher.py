"""File watcher for Claude Code transcripts."""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from aiana.config import get_claude_projects_dir, load_config
from aiana.models import Message
from aiana.storage import AianaStorage

logger = logging.getLogger(__name__)


class TranscriptHandler(FileSystemEventHandler):
    """Handles file system events for transcript files."""

    def __init__(
        self,
        storage: AianaStorage,
        on_message: Optional[Callable[[Message], None]] = None,
    ):
        """Initialize handler."""
        super().__init__()
        self.storage = storage
        self.on_message = on_message
        self.file_positions: dict[str, int] = {}
        self._lock = threading.Lock()

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        path = Path(event.src_path)
        if not path.suffix == ".jsonl":
            return

        self._process_new_lines(path)

    def _process_new_lines(self, path: Path) -> None:
        """Process new lines added to a file."""
        with self._lock:
            str_path = str(path)
            pos = self.file_positions.get(str_path, 0)

            try:
                with open(path) as f:
                    f.seek(pos)
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            data = json.loads(line)
                            session_id = self._extract_session_id(path, data)
                            if session_id:
                                message = Message.from_jsonl(session_id, data)
                                if message:
                                    self.storage.append_message(message)
                                    if self.on_message:
                                        self.on_message(message)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in {path}")
                            continue

                    self.file_positions[str_path] = f.tell()

            except FileNotFoundError:
                # File was deleted
                if str_path in self.file_positions:
                    del self.file_positions[str_path]
            except PermissionError:
                logger.warning(f"Permission denied: {path}")

    def _extract_session_id(self, path: Path, data: dict) -> Optional[str]:
        """Extract session ID from path or data."""
        # Try to get from data first
        if "sessionId" in data:
            return data["sessionId"]

        # Otherwise derive from filename
        if path.stem and not path.stem.startswith("agent-"):
            return path.stem

        return None

    def reset_position(self, path: Path) -> None:
        """Reset file position to start."""
        with self._lock:
            self.file_positions[str(path)] = 0


class TranscriptWatcher:
    """Watches Claude Code transcript files for changes."""

    def __init__(
        self,
        storage: Optional[AianaStorage] = None,
        on_message: Optional[Callable[[Message], None]] = None,
    ):
        """Initialize watcher."""
        self.config = load_config()
        self.storage = storage or AianaStorage()
        self.on_message = on_message

        self.projects_dir = get_claude_projects_dir()
        self.handler = TranscriptHandler(self.storage, on_message)
        self.observer: Optional[Observer] = None
        self._running = False

    def start(self) -> None:
        """Start watching for file changes."""
        if self._running:
            return

        if not self.projects_dir.exists():
            logger.warning(f"Claude projects directory not found: {self.projects_dir}")
            self.projects_dir.mkdir(parents=True, exist_ok=True)

        self.observer = Observer()
        self.observer.schedule(
            self.handler,
            str(self.projects_dir),
            recursive=True,
        )
        self.observer.start()
        self._running = True
        logger.info(f"Started watching {self.projects_dir}")

    def stop(self) -> None:
        """Stop watching for file changes."""
        if not self._running or not self.observer:
            return

        self.observer.stop()
        self.observer.join(timeout=5)
        self._running = False
        logger.info("Stopped watching")

    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running

    def scan_existing(self) -> int:
        """Scan and import existing transcript files."""
        if not self.projects_dir.exists():
            return 0

        count = 0
        for jsonl_file in self.projects_dir.rglob("*.jsonl"):
            if jsonl_file.name.startswith("agent-"):
                continue  # Skip agent files

            try:
                self.handler.reset_position(jsonl_file)
                self.handler._process_new_lines(jsonl_file)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to import {jsonl_file}: {e}")

        return count


class WatcherDaemon:
    """Background daemon for watching transcripts."""

    def __init__(self):
        """Initialize daemon."""
        self.watcher: Optional[TranscriptWatcher] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self, background: bool = True) -> None:
        """Start the daemon."""
        self.watcher = TranscriptWatcher()

        if background:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        else:
            self._run()

    def _run(self) -> None:
        """Run the watcher loop."""
        if not self.watcher:
            return

        self.watcher.start()

        try:
            while not self._stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.watcher.stop()

    def stop(self) -> None:
        """Stop the daemon."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def is_running(self) -> bool:
        """Check if daemon is running."""
        return self.watcher is not None and self.watcher.is_running()
