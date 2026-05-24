"""Shared helpers for cron and webhook tool scripts.

Consolidates the identical load/save/sanitize patterns that were
duplicated in ``cron_tools/_shared.py`` and ``webhook_tools/_shared.py``.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

try:  # pragma: no cover - platform import branch
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment]


@contextmanager
def locked_json(path: Path):
    """Advisory lock for read-modify-write JSON tool operations."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock_f:
        if fcntl is not None:
            fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_f, fcntl.LOCK_UN)


def sanitize_name(raw: str) -> str:
    """Lowercase and normalize a name to ``[a-z0-9-]``."""
    slug = raw.lower()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")


def load_collection_or_default(path: Path, key: str) -> dict[str, Any]:
    """Load a JSON file or return ``{key: []}`` if missing/corrupt.

    *key* is the top-level list field (e.g. ``"jobs"`` or ``"hooks"``).
    """
    if not path.exists():
        return {key: []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {key: []}
    if not isinstance(data, dict):
        return {key: []}
    if not isinstance(data.get(key), list):
        return {key: []}
    return data


def load_collection_strict(path: Path, key: str) -> dict[str, Any]:
    """Load a JSON file and raise on malformed structure.

    *key* is the top-level list field (e.g. ``"jobs"`` or ``"hooks"``).
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get(key), list):
        msg = f"Corrupt {path.name} -- cannot parse"
        raise TypeError(msg)
    return data


def save_collection(path: Path, data: dict[str, Any]) -> None:
    """Persist a JSON collection with stable formatting and atomic replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def update_collection(
    path: Path,
    key: str,
    mutator: Callable[[dict[str, Any]], None],
    *,
    strict: bool = False,
) -> dict[str, Any]:
    """Lock, reload latest collection, mutate, and save atomically."""
    with locked_json(path):
        data = load_collection_strict(path, key) if strict and path.exists() else load_collection_or_default(path, key)
        mutator(data)
        save_collection(path, data)
        return data


def available_ids(items: list[dict[str, Any]], id_field: str = "id") -> list[str]:
    """Return all IDs from a list of dicts for diagnostics."""
    return [str(item.get(id_field, "???")) for item in items]


def find_by_id(
    items: list[dict[str, Any]], item_id: str, id_field: str = "id"
) -> dict[str, Any] | None:
    """Find an item dict by its ID field."""
    return next((item for item in items if item.get(id_field) == item_id), None)
