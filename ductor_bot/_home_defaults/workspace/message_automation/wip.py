"""Reusable WIP state transitions for message automation.

This module is intentionally small and dependency-light so cron wrappers can
import it instead of duplicating WIP status logic in one-off scripts.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

DONE_STATUSES = {"done", "closed", "resolved", "complete", "completed"}
KP_STATUSES = {"kp_required", "blocked_kp"}
STUCK_STATUSES = {"stuck_no_response", "stuck_delivery_failed", "stuck_missing_route"}
INACTIVE_STATUSES = DONE_STATUSES | KP_STATUSES | STUCK_STATUSES


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def is_active(item: dict[str, Any]) -> bool:
    return (item.get("status") or "").lower() not in INACTIVE_STATUSES


def is_due(item: dict[str, Any], now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    next_check = parse_time(item.get("next_check_at"))
    return next_check is None or next_check <= now


def append_history(item: dict[str, Any], now: str, before: dict[str, Any], reason: str) -> None:
    item.setdefault("history", [])
    item["history"].append(
        {
            "timestamp": now,
            "before": before,
            "after": {
                "status": item.get("status"),
                "owner": item.get("owner"),
                "summary": item.get("summary"),
                "next_check_at": item.get("next_check_at"),
            },
            "reason": reason,
        }
    )
    item["history"] = item["history"][-20:]


def set_status(
    item: dict[str, Any],
    status: str,
    now: str,
    reason: str,
    *,
    next_hours: float | None = None,
) -> bool:
    before = {
        "status": item.get("status"),
        "owner": item.get("owner"),
        "summary": item.get("summary"),
        "next_check_at": item.get("next_check_at"),
    }
    changed = item.get("status") != status
    item["status"] = status
    item["last_event"] = reason
    item["last_event_at"] = now
    if next_hours is not None:
        item["next_check_at"] = iso(datetime.now(timezone.utc) + timedelta(hours=next_hours))
        changed = True
    if changed:
        append_history(item, now, before, reason)
    return changed


def should_block_for_kp(item: dict[str, Any]) -> bool:
    status = (item.get("status") or "").lower()
    owner = (item.get("owner") or "").lower()
    return status in KP_STATUSES or owner in {"kp", "user"}


def should_mark_stuck(item: dict[str, Any], *, max_checks: int = 3, max_age_hours: float = 24) -> bool:
    checks = int(item.get("check_count") or 0)
    if checks >= max_checks:
        return True
    last = parse_time(item.get("last_event_at")) or parse_time(item.get("created_at"))
    if not last:
        return False
    age_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600
    return age_hours >= max_age_hours
