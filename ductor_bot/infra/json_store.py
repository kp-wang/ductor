"""Atomic JSON file persistence.

Provides shared helpers for JSON-based storage used by cron, webhook,
and session managers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

from ductor_bot.infra.atomic_io import atomic_text_save

logger = logging.getLogger(__name__)

try:  # pragma: no cover - platform import branch
    import fcntl
except ImportError:  # Windows fallback keeps atomic writes, without advisory locks.
    fcntl = None  # type: ignore[assignment]


def atomic_json_save(path: Path, data: dict[str, Any] | list[Any]) -> None:
    """Write JSON atomically using temp file + rename."""
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    atomic_text_save(path, content)


def load_json(path: Path) -> dict[str, Any] | None:
    """Load JSON from file, return None if missing or corrupt."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
    except (json.JSONDecodeError, KeyError, TypeError, OSError):
        logger.warning("Corrupt or unreadable JSON file: %s", path)
        return None


def update_json_transaction(
    path: Path,
    default: dict[str, Any] | list[Any],
    mutator: Callable[[dict[str, Any] | list[Any]], None],
) -> dict[str, Any] | list[Any]:
    """Lock, reload, mutate, and atomically persist a JSON document.

    Use this for read-modify-write workflows where a plain atomic save is not
    enough to prevent lost updates from concurrent observers or tool scripts.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock_f:
        if fcntl is not None:
            fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            current = load_json(path)
            data = current if current is not None else default
            mutator(data)
            atomic_json_save(path, data)
            return data
        finally:
            if fcntl is not None:
                fcntl.flock(lock_f, fcntl.LOCK_UN)
