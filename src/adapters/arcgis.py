"""ArcGIS REST feature/map service layers (no key needed for public layers)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import date, timedelta
from typing import Any

import httpx

from ..models import ArcGISSource
from .http import SourceError, get_json

log = logging.getLogger(__name__)

_layer_meta_cache: dict[str, dict[str, Any]] = {}


async def _json(client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> dict[str, Any]:
    data = await get_json(client, url, params=params)
    if isinstance(data, dict) and "error" in data:
        err = data["error"]
        raise SourceError(f"ArcGIS error {err.get('code')}: {err.get('message')} {err.get('details') or ''}".strip())
    return data


async def layer_meta(client: httpx.AsyncClient, layer_url: str) -> dict[str, Any]:
    if layer_url not in _layer_meta_cache:
        _layer_meta_cache[layer_url] = await _json(client, layer_url, {"f": "json"})
    return _layer_meta_cache[layer_url]


async def resolve_layers(client: httpx.AsyncClient, source: ArcGISSource, date_from: date, date_to: date) -> list[str]:
    if source.layer_url:
        return [source.layer_url]
    if not (source.service_url and source.layer_name_template):
        raise SourceError("ArcGIS source needs layer_url or service_url + layer_name_template")
    service = await _json(client, source.service_url, {"f": "json"})
    by_name = {str(layer.get("name", "")).strip().lower(): layer.get("id") for layer in service.get("layers", [])}
    urls = []
    for year in range(date_to.year, date_from.year - 1, -1):
        wanted = source.layer_name_template.format(year=year).strip().lower()
        if wanted in by_name:
            urls.append(f"{source.service_url.rstrip('/')}/{by_name[wanted]}")
        else:
            log.warning("ArcGIS layer %r not found in %s", wanted, source.service_url)
    if not urls:
        raise SourceError(f"No yearly layer matching {source.layer_name_template!r} for {date_from.year}-{date_to.year}")
    return urls


def _date_literals(field_type: str, day: date) -> list[str]:
    if field_type == "esriFieldTypeDateOnly":
        return [f"DATE '{day.isoformat()}'"]
    # Hosted services accept TIMESTAMP; older ArcGIS Server versions want the legacy DATE 'Y-m-d H:M:S' form.
    return [f"TIMESTAMP '{day.isoformat()} 00:00:00'", f"DATE '{day.isoformat()} 00:00:00'"]


async def fetch_pages(
    client: httpx.AsyncClient,
    source: ArcGISSource,
    date_from: date,
    date_to: date,
    page_size: int,
) -> AsyncIterator[list[dict[str, Any]]]:
    for layer_url in await resolve_layers(client, source, date_from, date_to):
        async for page in _fetch_layer(client, layer_url, source, date_from, date_to, page_size):
            yield page


async def _fetch_layer(
    client: httpx.AsyncClient,
    layer_url: str,
    source: ArcGISSource,
    date_from: date,
    date_to: date,
    page_size: int,
) -> AsyncIterator[list[dict[str, Any]]]:
    meta = await layer_meta(client, layer_url)
    fields = {f["name"].lower(): f for f in meta.get("fields", [])}
    date_meta = fields.get(source.date_field.lower())
    if not date_meta:
        raise SourceError(f"Date field {source.date_field!r} no longer exists on {layer_url}")
    date_field = date_meta["name"]
    max_records = int(meta.get("maxRecordCount") or 1000)
    size = max(1, min(page_size, max_records))
    end = date_to + timedelta(days=1)
    query_url = f"{layer_url.rstrip('/')}/query"

    lo_options = _date_literals(date_meta.get("type", ""), date_from)
    hi_options = _date_literals(date_meta.get("type", ""), end)
    last_error: SourceError | None = None
    for lo, hi in zip(lo_options, hi_options):
        where = f"{date_field} >= {lo} AND {date_field} < {hi}"
        if source.extra_where:
            where += f" AND ({source.extra_where})"
        offset = 0
        try:
            while True:
                params = {
                    "where": where,
                    "outFields": "*",
                    "orderByFields": f"{date_field} DESC",
                    "resultOffset": offset,
                    "resultRecordCount": size,
                    "returnGeometry": "true",
                    "outSR": 4326,
                    "f": "json",
                }
                data = await _json(client, query_url, params)
                features = data.get("features") or []
                rows = []
                for feat in features:
                    row = dict(feat.get("attributes") or {})
                    geom = feat.get("geometry") or {}
                    if isinstance(geom, dict) and "x" in geom and "y" in geom:
                        row["__lon"], row["__lat"] = geom.get("x"), geom.get("y")
                    rows.append(row)
                if rows:
                    yield rows
                if not rows or not (data.get("exceededTransferLimit") or len(rows) >= size):
                    return
                offset += len(rows)
        except SourceError as exc:
            if offset > 0:  # failed mid-way: the date syntax worked, so this is a real error
                raise
            last_error = exc
            log.debug("ArcGIS date syntax %s rejected by %s: %s", lo, layer_url, exc)
    raise last_error or SourceError(f"ArcGIS query failed for {layer_url}")
