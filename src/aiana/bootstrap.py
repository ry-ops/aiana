"""Auto-bootstrap AIANA with user preferences on first run."""

import os
from pathlib import Path
from typing import Optional

# Bootstrap preferences are bundled with the package
BOOTSTRAP_DIR = Path(__file__).parent.parent.parent / "bootstrap"
BOOTSTRAP_MARKER = Path.home() / ".aiana" / ".bootstrapped"


def get_bootstrap_file() -> Optional[Path]:
    """Get the path to the bootstrap preferences file."""
    prefs_file = BOOTSTRAP_DIR / "user-preferences.md"
    if prefs_file.exists():
        return prefs_file
    return None


def is_bootstrapped() -> bool:
    """Check if AIANA has already been bootstrapped."""
    return BOOTSTRAP_MARKER.exists()


def mark_bootstrapped() -> None:
    """Mark AIANA as bootstrapped."""
    BOOTSTRAP_MARKER.parent.mkdir(parents=True, exist_ok=True)
    BOOTSTRAP_MARKER.write_text("1")


def load_bootstrap_preferences() -> list[dict]:
    """Parse bootstrap preferences file into memory entries."""
    prefs_file = get_bootstrap_file()
    if not prefs_file:
        return []

    content = prefs_file.read_text()
    memories = []

    # Parse sections into separate memories
    current_section = None
    current_content = []

    for line in content.split("\n"):
        if line.startswith("## "):
            # Save previous section
            if current_section and current_content:
                memories.append({
                    "content": f"{current_section}\n" + "\n".join(current_content),
                    "memory_type": "preference",
                    "section": current_section,
                })
            current_section = line[3:].strip()
            current_content = []
        elif line.startswith("### "):
            # Subsection - include in content
            current_content.append(line)
        elif line.strip():
            current_content.append(line)

    # Save last section
    if current_section and current_content:
        memories.append({
            "content": f"{current_section}\n" + "\n".join(current_content),
            "memory_type": "preference",
            "section": current_section,
        })

    return memories


def auto_bootstrap(force: bool = False) -> dict:
    """Auto-bootstrap AIANA on first run.

    Args:
        force: Force re-bootstrap even if already done.

    Returns:
        Dict with bootstrap status and count.
    """
    if is_bootstrapped() and not force:
        return {"status": "already_bootstrapped", "count": 0}

    memories = load_bootstrap_preferences()
    if not memories:
        return {"status": "no_bootstrap_file", "count": 0}

    # Try to load into Mem0 first, fall back to Qdrant
    loaded = 0
    backend = None

    try:
        from aiana.storage.mem0 import Mem0Storage
        storage = Mem0Storage()
        backend = "mem0"

        for mem in memories:
            storage.add_memory(
                content=mem["content"],
                session_id="bootstrap",
                project="_global",  # Global preferences
                memory_type=mem["memory_type"],
                metadata={"section": mem.get("section", "unknown"), "source": "bootstrap"},
            )
            loaded += 1

    except Exception:
        # Fall back to Qdrant
        try:
            from aiana.embeddings import get_embedder
            from aiana.storage.qdrant import QdrantStorage

            embedder = get_embedder()
            storage = QdrantStorage(embedder=embedder)
            backend = "qdrant"

            for mem in memories:
                storage.add_memory(
                    content=mem["content"],
                    session_id="bootstrap",
                    project="_global",
                    memory_type=mem["memory_type"],
                    metadata={"section": mem.get("section", "unknown"), "source": "bootstrap"},
                )
                loaded += 1

        except Exception as e:
            return {"status": "error", "error": str(e), "count": 0}

    if loaded > 0:
        mark_bootstrapped()

    return {
        "status": "success",
        "count": loaded,
        "backend": backend,
        "sections": [m.get("section") for m in memories],
    }


def reset_bootstrap() -> None:
    """Reset bootstrap marker to allow re-bootstrap."""
    if BOOTSTRAP_MARKER.exists():
        BOOTSTRAP_MARKER.unlink()
