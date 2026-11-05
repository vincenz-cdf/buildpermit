"""Shared HTTP helper with retries for all open-data platforms."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)

USER_AGENT = "building-permit-leads-actor/1.0 (Apify; open-data client)"
RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}


class SourceError(Exception):
    """A source failed in a way that retrying will not fix (bad query, removed dataset...)."""


async def get_json(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    auth: tuple[str, str] | None = None,
    attempts: int = 4,
) -> Any:
    delay = 2.0
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = await client.get(url, params=params, headers=headers, auth=auth)
            if response.status_code in RETRY_STATUS:
                raise httpx.HTTPStatusError(f"HTTP {response.status_code}", request=response.request, response=response)
            if response.status_code >= 400:
                body = response.text[:300].replace("\n", " ")
                raise SourceError(f"HTTP {response.status_code} from {url}: {body}")
            return response.json()
        except (httpx.TransportError, httpx.HTTPStatusError, ValueError) as exc:
            last_error = exc
            if attempt == attempts:
                break
            retry_after = None
            if isinstance(exc, httpx.HTTPStatusError):
                retry_after = exc.response.headers.get("retry-after")
            wait = float(retry_after) if retry_after and retry_after.isdigit() else delay
            log.debug("Retrying %s in %.0fs after %s", url, wait, exc)
            await asyncio.sleep(min(wait, 30))
            delay *= 2
    raise SourceError(f"{url} failed after {attempts} attempts: {last_error}")


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(90.0, connect=20.0),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
