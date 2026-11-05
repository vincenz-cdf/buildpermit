"""Platform adapters. Each yields pages of raw rows, newest first, for a date window."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import httpx

from ..models import ArcGISSource, CartoSource, CkanSource, SocrataSource, Source
from . import arcgis, carto, ckan, socrata
from .socrata import SocrataAuth


def fetch_pages(
    client: httpx.AsyncClient,
    source: Source,
    date_from: date,
    date_to: date,
    page_size: int,
    socrata_auth: SocrataAuth,
) -> AsyncIterator[list[dict[str, Any]]]:
    if isinstance(source, SocrataSource):
        return socrata.fetch_pages(client, source, date_from, date_to, page_size, socrata_auth)
    if isinstance(source, ArcGISSource):
        return arcgis.fetch_pages(client, source, date_from, date_to, page_size)
    if isinstance(source, CkanSource):
        return ckan.fetch_pages(client, source, date_from, date_to, page_size)
    if isinstance(source, CartoSource):
        return carto.fetch_pages(client, source, date_from, date_to, page_size)
    raise TypeError(f"Unknown source type {type(source)!r}")


__all__ = ["SocrataAuth", "fetch_pages"]
