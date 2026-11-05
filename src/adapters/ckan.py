"""CKAN DataStore SQL API (data.boston.gov, data.sanantonio.gov)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, timedelta
from typing import Any

import httpx

from ..models import CkanSource
from .http import SourceError, get_json


async def fetch_pages(
    client: httpx.AsyncClient,
    source: CkanSource,
    date_from: date,
    date_to: date,
    page_size: int,
) -> AsyncIterator[list[dict[str, Any]]]:
    url = f"{source.base_url.rstrip('/')}/api/3/action/datastore_search_sql"
    col = '"' + source.date_field.replace('"', '""') + '"'
    end = (date_to + timedelta(days=1)).isoformat()
    # Dates may be stored as text or timestamps; ISO text compares correctly either way.
    where = f"{col} >= '{date_from.isoformat()}' AND {col} < '{end}'"
    offset = 0
    while True:
        sql = (
            f'SELECT * FROM "{source.resource_id}" WHERE {where} '
            f"ORDER BY {col} DESC LIMIT {page_size} OFFSET {offset}"
        )
        data = await get_json(client, url, params={"sql": sql})
        if not data.get("success"):
            raise SourceError(f"CKAN error: {str(data.get('error'))[:300]}")
        rows = data["result"].get("records") or []
        for row in rows:
            row.pop("_full_text", None)
        if rows:
            yield rows
        if len(rows) < page_size:
            return
        offset += len(rows)
