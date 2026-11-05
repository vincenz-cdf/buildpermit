"""CARTO SQL API (phl.carto.com). Public tables need no key."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, timedelta
from typing import Any

import httpx

from ..models import CartoSource
from .http import SourceError, get_json


async def fetch_pages(
    client: httpx.AsyncClient,
    source: CartoSource,
    date_from: date,
    date_to: date,
    page_size: int,
) -> AsyncIterator[list[dict[str, Any]]]:
    url = f"{source.account_url.rstrip('/')}/api/v2/sql"
    col = source.date_field
    end = (date_to + timedelta(days=1)).isoformat()
    offset = 0
    while True:
        sql = (
            f"SELECT *, ST_Y(the_geom) AS __lat, ST_X(the_geom) AS __lon FROM {source.table} "
            f"WHERE {col} >= '{date_from.isoformat()}' AND {col} < '{end}' "
            f"ORDER BY {col} DESC LIMIT {page_size} OFFSET {offset}"
        )
        data = await get_json(client, url, params={"q": sql})
        if "error" in data:
            raise SourceError(f"CARTO error: {data['error']}")
        rows = data.get("rows") or []
        for row in rows:
            row.pop("the_geom", None)
            row.pop("the_geom_webmercator", None)
        if rows:
            yield rows
        if len(rows) < page_size:
            return
        offset += len(rows)
