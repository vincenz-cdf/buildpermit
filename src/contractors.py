"""Roll permits up into one row per contractor per city."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

_SUFFIX = re.compile(r"\b(llc|l\.l\.c|inc|incorporated|corp|corporation|co|company|ltd|lp|llp|pllc|pc)\b\.?", re.I)
_PUNCT = re.compile(r"[^a-z0-9 ]+")


def contractor_key(name: str) -> str:
    text = _SUFFIX.sub(" ", name.lower())
    text = _PUNCT.sub(" ", text)
    return " ".join(text.split())


def rollup(permits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for p in permits:
        name = p.get("contractor_name")
        if not name:
            continue
        key = contractor_key(name)
        if key:
            groups.setdefault((p["city_key"], key), []).append(p)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows = []
    for (city_key, key), items in groups.items():
        names = Counter(i["contractor_name"] for i in items)
        values = [i["project_value"] for i in items if i.get("project_value")]
        trades = Counter(t for i in items for t in (i.get("trades") or []))
        dates = sorted(i["issue_date"] for i in items if i.get("issue_date"))

        def first(field: str) -> Any:
            for i in items:
                if i.get(field):
                    return i[field]
            return None

        rows.append({
            "record_type": "contractor",
            "record_id": f"{city_key}:contractor:{key}",
            "city_key": city_key,
            "city": items[0]["city"],
            "state": items[0]["state"],
            "contractor_name": names.most_common(1)[0][0],
            "contractor_phone": first("contractor_phone"),
            "contractor_email": first("contractor_email"),
            "contractor_license": first("contractor_license"),
            "contractor_address": first("contractor_address"),
            "contractor_city": first("contractor_city"),
            "contractor_state": first("contractor_state"),
            "contractor_zip": first("contractor_zip"),
            "permit_count": len(items),
            "total_project_value": round(sum(values), 2) if values else None,
            "avg_project_value": round(sum(values) / len(values), 2) if values else None,
            "top_trades": [t for t, _ in trades.most_common(5)],
            "trade_counts": dict(trades.most_common()),
            "first_issue_date": dates[0] if dates else None,
            "latest_issue_date": dates[-1] if dates else None,
            "recent_permits": [
                {"permit_number": i["permit_number"], "issue_date": i.get("issue_date"), "address": i.get("address"),
                 "primary_trade": i.get("primary_trade"), "project_value": i.get("project_value")}
                for i in sorted(items, key=lambda x: x.get("issue_date") or "", reverse=True)[:5]
            ],
            "scraped_at": now,
        })
    rows.sort(key=lambda r: (r["permit_count"], r["total_project_value"] or 0), reverse=True)
    return rows
