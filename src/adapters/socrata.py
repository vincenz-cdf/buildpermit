"""Socrata SODA API (data.cityofchicago.org, data.cityofnewyork.us, ...)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import httpx

from ..models import SocrataSource
from ..parsing import parse_date
from .http import SourceError, get_json

log = logging.getLogger(__name__)


@dataclass
class SocrataAuth:
    app_token: str | None = None
    key_id: str | None = None
    key_secret: str | None = None
    disabled: bool = False  # set when the credentials are rejected, so later calls go anonymous

    def headers(self) -> dict[str, str]:
        if self.app_token and not self.disabled:
            return {"X-App-Token": self.app_token}
        return {}

    def basic(self) -> tuple[str, str] | None:
        if self.key_id and self.key_secret and not self.disabled and not self.app_token:
            return (self.key_id, self.key_secret)
        return None

    @property
    def active(self) -> bool:
        return not self.disabled and bool(self.app_token or (self.key_id and self.key_secret))


async def _get(client: httpx.AsyncClient, url: str, params: dict[str, Any], auth: SocrataAuth) -> Any:
    try:
        return await get_json(client, url, params=params, headers=auth.headers(), auth=auth.basic())
    except SourceError as exc:
        if auth.active and ("HTTP 401" in str(exc) or "HTTP 403" in str(exc)):
            log.warning("Socrata rejected the app token / API key; continuing without it (lower rate limits).")
            auth.disabled = True
            return await get_json(client, url, params=params)
        raise


async def fetch_pages(
    client: httpx.AsyncClient,
    source: SocrataSource,
    date_from: date,
    date_to: date,
    page_size: int,
    auth: SocrataAuth,
) -> AsyncIterator[list[dict[str, Any]]]:
    url = f"https://{source.domain}/resource/{source.dataset}.json"
    end = (date_to + timedelta(days=1)).isoformat()
    where_parts = []
    if source.server_date_filter:
        f = source.date_field
        where_parts.append(f"{f} >= '{date_from.isoformat()}T00:00:00' AND {f} < '{end}T00:00:00'")
        order = f"{f} DESC, :id"
    else:
        order = source.order or ":id DESC"
    if source.extra_where:
        where_parts.append(f"({source.extra_where})")

    offset = 0
    pages_all_older = 0
    while True:
        params: dict[str, Any] = {"$limit": page_size, "$offset": offset, "$order": order}
        if where_parts:
            params["$where"] = " AND ".join(where_parts)
        rows = await _get(client, url, params, auth)
        if not isinstance(rows, list):
            raise SourceError(f"Unexpected Socrata response from {url}: {str(rows)[:200]}")
        if not rows:
            return
        yield rows
        if len(rows) < page_size:
            return
        offset += len(rows)
        if not source.server_date_filter:
            # Rows come newest-first by row id; stop once whole pages fall before the requested window.
            dates = [parse_date(r.get(source.date_field)) for r in rows]
            if all(d is None or d < date_from for d in dates):
                pages_all_older += 1
                if pages_all_older >= 2:
                    return
            else:
                pages_all_older = 0
