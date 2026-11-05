"""Apify Actor entry point: building permit leads from official US/Canada open-data portals."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from apify import Actor

from .adapters import SocrataAuth
from .adapters.http import make_client
from .cities import CITIES, CITY_BY_KEY
from .collect import CityResult, collect_city
from .contractors import rollup
from .enrich import TRADES
from .filters import Filters
from .models import City
from .parsing import parse_date
from .state import STORE_NAME, SeenStore, state_key

PERMIT_EVENT = "permit"
CONTRACTOR_EVENT = "contractor"
CONCURRENCY = 6
PUSH_CHUNK = 500


class InputError(ValueError):
    pass


@dataclass
class RunConfig:
    cities: list[City]
    filters: Filters
    output_mode: str
    max_per_city: int
    max_total: int
    only_new: bool
    state_name: str
    include_raw: bool
    health_check: bool
    socrata: SocrataAuth


def _str_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        value = value.replace(";", ",").split(",")
    return [str(v).strip() for v in value if str(v).strip()]


def parse_input(inp: dict[str, Any], today: date) -> RunConfig:
    keys = [k.lower() for k in _str_list(inp.get("cities"))]
    states = {s.upper() for s in _str_list(inp.get("states"))}
    unknown = [k for k in keys if k not in CITY_BY_KEY]
    if unknown:
        raise InputError(f"Unknown city keys: {', '.join(unknown)}. Valid keys: {', '.join(CITY_BY_KEY)}")
    if keys or states:
        cities = [CITY_BY_KEY[k] for k in keys]
        cities += [c for c in CITIES if c.state in states and c not in cities]
    else:
        cities = list(CITIES)
    if not cities:
        raise InputError(f"No supported city in states {sorted(states)}.")

    date_to = parse_date(inp.get("dateTo")) or today
    date_from = parse_date(inp.get("dateFrom"))
    if date_from is None:
        days = int(inp.get("lastNDays") or 30)
        date_from = date_to - timedelta(days=max(days, 1) - 1)
    if date_from > date_to:
        raise InputError(f"dateFrom ({date_from}) is after dateTo ({date_to}).")

    trades = {t.lower() for t in _str_list(inp.get("trades"))}
    bad_trades = trades - set(TRADES) - {"other"}
    if bad_trades:
        raise InputError(f"Unknown trades: {', '.join(sorted(bad_trades))}. Valid: {', '.join(TRADES)}")

    min_value = inp.get("minProjectValue")
    filters = Filters(
        date_from=date_from,
        date_to=date_to,
        trades=frozenset(trades),
        keywords=tuple(k.lower() for k in _str_list(inp.get("keywords"))),
        zip_codes=tuple(_str_list(inp.get("zipCodes"))),
        min_value=float(min_value) if min_value not in (None, "", 0) else None,
        property_type=inp.get("propertyType") or "any",
        require_contact=inp.get("requireContact") or "none",
        exclude_owner_builder=bool(inp.get("excludeOwnerBuilder")),
        exclude_closed=bool(inp.get("excludeClosed")),
        min_grade=(inp.get("minLeadGrade") or "COLD").upper(),
    )
    token = inp.get("socrataAppToken") or os.environ.get("SOCRATA_APP_TOKEN")
    return RunConfig(
        cities=cities,
        filters=filters,
        output_mode=inp.get("outputMode") or "permits",
        max_per_city=max(1, int(inp.get("maxResultsPerCity") or 500)),
        max_total=int(inp.get("maxResults") or 0),
        only_new=bool(inp.get("onlyNew")),
        state_name=inp.get("stateKey") or "default",
        include_raw=bool(inp.get("includeRaw")),
        health_check=bool(inp.get("healthCheck")),
        socrata=SocrataAuth(
            app_token=token or None,
            key_id=os.environ.get("SOCRATA_KEY_ID") or None,
            key_secret=os.environ.get("SOCRATA_KEY_SECRET") or None,
        ),
    )


async def run_health_check(cfg: RunConfig, today: date) -> None:
    """Check every selected source: does it answer, and how fresh is its newest permit?"""
    filters = Filters(date_from=today - timedelta(days=60), date_to=today)
    sem = asyncio.Semaphore(CONCURRENCY)
    async with make_client() as client:

        async def one(city: City) -> CityResult:
            async with sem:
                return await collect_city(client, city, filters, 1, 400, cfg.socrata, today)

        results = await asyncio.gather(*(one(c) for c in cfg.cities))

    report = []
    for r in results:
        newest = r.newest_issue_date
        age = (today - date.fromisoformat(newest)).days if newest else None
        status = r.status
        if status == "ok":
            status = "empty" if newest is None else "stale" if age is not None and age > 14 else "ok"
        report.append({**r.summary(), "status": status, "days_since_newest_permit": age})
        Actor.log.info(f"{status.upper():7} {r.city.key:22} newest={newest} age={age}d errors={len(r.errors)}")
    await Actor.set_value("HEALTH", {"checked_at": datetime.now(timezone.utc).isoformat(), "sources": report})
    bad = [x["city_key"] for x in report if x["status"] != "ok"]
    await Actor.set_status_message(f"Health check: {len(report) - len(bad)}/{len(report)} OK" + (f"; check {', '.join(bad)}" if bad else ""))


async def main() -> None:
    async with Actor:
        today = datetime.now(timezone.utc).date()
        try:
            cfg = parse_input(await Actor.get_input() or {}, today)
        except InputError as exc:
            await Actor.fail(status_message=str(exc))
            return

        if cfg.health_check:
            await run_health_check(cfg, today)
            return

        f = cfg.filters
        Actor.log.info(
            f"{len(cfg.cities)} cities, {f.date_from} to {f.date_to}, mode={cfg.output_mode}, "
            f"maxResultsPerCity={cfg.max_per_city}, onlyNew={cfg.only_new}, socrataToken={'yes' if cfg.socrata.active else 'no'}"
        )

        seen: SeenStore | None = None
        state_store = None
        if cfg.only_new:
            state_store = await Actor.open_key_value_store(name=STORE_NAME)
            seen = SeenStore(await state_store.get_value(state_key(cfg.state_name)))
            Actor.log.info(f"Only-new mode: {len(seen.seen)} permits already delivered under stateKey={cfg.state_name!r}")

        scan_limit = min(200_000, max(10_000, cfg.max_per_city * 25))
        push_permits = cfg.output_mode in ("permits", "both")
        lock = asyncio.Lock()
        totals = {"permits": 0, "contractors": 0}
        stop = asyncio.Event()
        budget_hit = asyncio.Event()
        all_matched: list[dict[str, Any]] = []
        summaries: list[dict[str, Any]] = []

        async def deliver(records: list[dict[str, Any]]) -> None:
            async with lock:
                for i in range(0, len(records), PUSH_CHUNK):
                    if stop.is_set():
                        return
                    chunk = records[i : i + PUSH_CHUNK]
                    if cfg.max_total:
                        chunk = chunk[: max(0, cfg.max_total - totals["permits"])]
                    if not chunk:
                        stop.set()
                        return
                    res = await Actor.push_data(chunk, charged_event_name=PERMIT_EVENT)
                    delivered = chunk[: res.charged_count] if res.event_charge_limit_reached else chunk
                    totals["permits"] += len(delivered)
                    if seen is not None:
                        seen.mark(delivered)
                    if res.event_charge_limit_reached:
                        Actor.log.info("Reached the maximum cost you set for this run; stopping.")
                        budget_hit.set()
                        stop.set()
                        return
                    if cfg.max_total and totals["permits"] >= cfg.max_total:
                        stop.set()
                        return

        sem = asyncio.Semaphore(CONCURRENCY)
        async with make_client() as client:

            async def one(city: City) -> None:
                async with sem:
                    if stop.is_set():
                        return
                    r = await collect_city(
                        client, city, cfg.filters, cfg.max_per_city, scan_limit, cfg.socrata, today, seen, cfg.include_raw
                    )
                summaries.append(r.summary())
                Actor.log.info(
                    f"{city.key}: {len(r.records)} matched / {r.in_window} in window / {r.scanned} scanned"
                    + (f" / skipped {r.skipped_seen} already seen" if r.skipped_seen else "")
                    + (f" / ERRORS: {'; '.join(r.errors)}" if r.errors else "")
                )
                if push_permits:
                    await deliver(r.records)
                else:
                    all_matched.extend(r.records)
                if cfg.output_mode == "both":
                    all_matched.extend(r.records)

            await asyncio.gather(*(one(c) for c in cfg.cities))

        if cfg.output_mode in ("contractors", "both") and not budget_hit.is_set():
            rows = rollup(all_matched)
            if cfg.max_total and cfg.output_mode == "contractors":
                rows = rows[: cfg.max_total]
            for i in range(0, len(rows), PUSH_CHUNK):
                res = await Actor.push_data(rows[i : i + PUSH_CHUNK], charged_event_name=CONTRACTOR_EVENT)
                totals["contractors"] += res.charged_count if res.event_charge_limit_reached else len(rows[i : i + PUSH_CHUNK])
                if res.event_charge_limit_reached:
                    break
            if cfg.output_mode == "contractors" and seen is not None:
                seen.mark(all_matched)

        if seen is not None and state_store is not None:
            await state_store.set_value(state_key(cfg.state_name), seen.pruned(today))

        failed = [s["city_key"] for s in summaries if s["status"] == "error"]
        partial = [s["city_key"] for s in summaries if s["status"] == "partial"]
        await Actor.set_value("RUN_SUMMARY", {
            "date_from": f.date_from.isoformat(),
            "date_to": f.date_to.isoformat(),
            "permits_delivered": totals["permits"],
            "contractor_rows_delivered": totals["contractors"],
            "cities_failed": failed,
            "cities_partial": partial,
            "cities": sorted(summaries, key=lambda s: s["city_key"]),
        })

        msg = f"Delivered {totals['permits']} permits"
        if cfg.output_mode != "permits":
            msg += f" and {totals['contractors']} contractor rows"
        msg += f" from {len(summaries) - len(failed)}/{len(cfg.cities)} cities"
        if failed:
            msg += f". Unavailable right now: {', '.join(failed)} (see RUN_SUMMARY)"
        if failed and len(failed) == len(cfg.cities):
            await Actor.fail(status_message=msg)
            return
        await Actor.set_status_message(msg)
