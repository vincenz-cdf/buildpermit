"""Fetch, normalize and filter permits for one city. Independent of the Apify SDK so it can be tested locally."""

from __future__ import annotations

import logging
import time
from contextlib import aclosing
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import httpx

from .adapters import SocrataAuth, fetch_pages
from .adapters.http import SourceError
from .filters import Filters
from .models import City
from .normalize import normalize
from .state import SeenStore

log = logging.getLogger(__name__)

PAGE_SIZE = {"socrata": 2000, "arcgis": 2000, "ckan": 1000, "carto": 2000}


@dataclass
class CityResult:
    city: City
    records: list[dict[str, Any]] = field(default_factory=list)
    scanned: int = 0
    in_window: int = 0
    skipped_seen: int = 0
    newest_issue_date: str | None = None
    hit_result_limit: bool = False
    hit_scan_limit: bool = False
    errors: list[str] = field(default_factory=list)
    sources_ok: int = 0
    seconds: float = 0.0

    @property
    def status(self) -> str:
        if self.errors and not self.sources_ok:
            return "error"
        if self.errors:
            return "partial"
        return "ok"

    def summary(self) -> dict[str, Any]:
        return {
            "city_key": self.city.key,
            "city": self.city.name,
            "state": self.city.state,
            "status": self.status,
            "matched": len(self.records),
            "rows_scanned": self.scanned,
            "rows_in_date_window": self.in_window,
            "skipped_already_seen": self.skipped_seen,
            "newest_issue_date_seen": self.newest_issue_date,
            "hit_max_results_per_city": self.hit_result_limit,
            "hit_scan_limit": self.hit_scan_limit,
            "errors": self.errors,
            "seconds": round(self.seconds, 1),
        }


async def collect_city(
    client: httpx.AsyncClient,
    city: City,
    filters: Filters,
    max_results: int,
    scan_limit: int,
    auth: SocrataAuth,
    today: date,
    seen: SeenStore | None = None,
    include_raw: bool = False,
) -> CityResult:
    result = CityResult(city=city)
    started = time.monotonic()
    ids: set[str] = set()
    df, dt = filters.date_from.isoformat(), filters.date_to.isoformat()

    for source in city.sources:
        if result.hit_result_limit or result.hit_scan_limit:
            break
        try:
            pages = fetch_pages(client, source, filters.date_from, filters.date_to, PAGE_SIZE[source.platform], auth)
            async with aclosing(pages):
                async for page in pages:
                    for raw in page:
                        result.scanned += 1
                        rec = normalize(raw, city, source, today)
                        if rec is None or rec["record_id"] in ids:
                            continue
                        ids.add(rec["record_id"])
                        issue = rec["issue_date"]
                        if issue and issue <= dt and (result.newest_issue_date is None or issue > result.newest_issue_date):
                            result.newest_issue_date = issue
                        if issue and df <= issue <= dt:
                            result.in_window += 1
                        if not filters.matches(rec):
                            continue
                        if seen is not None and not seen.is_new(rec["record_id"]):
                            result.skipped_seen += 1
                            continue
                        if include_raw:
                            rec["raw"] = {k: v for k, v in raw.items() if not k.startswith("__")}
                        result.records.append(rec)
                        if len(result.records) >= max_results:
                            result.hit_result_limit = True
                            break
                    if result.hit_result_limit:
                        break
                    if result.scanned >= scan_limit:
                        result.hit_scan_limit = True
                        break
            result.sources_ok += 1
        except (SourceError, httpx.HTTPError) as exc:
            msg = f"{source.label}: {exc}"
            log.warning("%s (%s) failed: %s", city.name, city.key, msg)
            result.errors.append(msg[:500])
        except Exception as exc:  # noqa: BLE001 - one broken source must never fail the whole run
            msg = f"{source.label}: unexpected {type(exc).__name__}: {exc}"
            log.exception("%s (%s) failed unexpectedly", city.name, city.key)
            result.errors.append(msg[:500])

    # Newest permits first across all of a city's sources.
    result.records.sort(key=lambda r: r.get("issue_date") or "", reverse=True)
    result.seconds = time.monotonic() - started
    return result
