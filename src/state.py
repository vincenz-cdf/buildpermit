"""Remembers which permits were already delivered, for the "only new permits" mode."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

STORE_NAME = "building-permit-leads-state"
KEEP_DAYS = 400


def state_key(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9!\-_.'()]", "-", name or "default")[:200]
    return f"seen-{safe}"


class SeenStore:
    def __init__(self, data: dict[str, str] | None):
        self.seen: dict[str, str] = dict(data or {})

    def is_new(self, record_id: str) -> bool:
        return record_id not in self.seen

    def mark(self, records: list[dict[str, Any]]) -> None:
        for r in records:
            self.seen[r["record_id"]] = r.get("issue_date") or ""

    def pruned(self, today: date) -> dict[str, str]:
        cutoff = (today - timedelta(days=KEEP_DAYS)).isoformat()
        return {k: v for k, v in self.seen.items() if not v or v >= cutoff}
