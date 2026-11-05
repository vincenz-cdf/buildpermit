"""Source and city definitions used by the registry in ``cities.py``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Union

# A field spec tells the normalizer where a value lives in a raw source row:
#   "name"            -> raw["name"]
#   ("a", "b")        -> first non-empty of raw["a"], raw["b"]
#   callable(raw)     -> computed value
FieldSpec = Union[str, tuple[str, ...], Callable[[dict[str, Any]], Any]]


@dataclass(frozen=True)
class SocrataSource:
    domain: str
    dataset: str
    date_field: str
    # False when the date column is stored as text the API cannot compare (e.g. Dallas "MM/DD/YY").
    # Rows are then read newest-first by ``order`` and filtered by date on our side.
    server_date_filter: bool = True
    order: str | None = None
    extra_where: str | None = None
    fields: dict[str, FieldSpec] = field(default_factory=dict)
    fixed: dict[str, Any] = field(default_factory=dict)

    platform = "socrata"

    @property
    def label(self) -> str:
        return f"socrata:{self.domain}/{self.dataset}"

    @property
    def page_url(self) -> str:
        return f"https://{self.domain}/d/{self.dataset}"


@dataclass(frozen=True)
class ArcGISSource:
    date_field: str
    # Either a fixed layer URL (.../FeatureServer/0) ...
    layer_url: str | None = None
    # ... or a service URL plus a layer-name template with "{year}", for cities that publish one layer per year.
    service_url: str | None = None
    layer_name_template: str | None = None
    extra_where: str | None = None
    fields: dict[str, FieldSpec] = field(default_factory=dict)
    fixed: dict[str, Any] = field(default_factory=dict)

    platform = "arcgis"

    @property
    def label(self) -> str:
        return f"arcgis:{self.layer_url or self.service_url}"

    @property
    def page_url(self) -> str:
        return self.layer_url or self.service_url or ""


@dataclass(frozen=True)
class CkanSource:
    base_url: str
    resource_id: str
    date_field: str
    fields: dict[str, FieldSpec] = field(default_factory=dict)
    fixed: dict[str, Any] = field(default_factory=dict)

    platform = "ckan"

    @property
    def label(self) -> str:
        return f"ckan:{self.base_url}/{self.resource_id}"

    @property
    def page_url(self) -> str:
        return f"{self.base_url}/dataset?res_id={self.resource_id}"


@dataclass(frozen=True)
class CartoSource:
    account_url: str  # e.g. https://phl.carto.com
    table: str
    date_field: str
    fields: dict[str, FieldSpec] = field(default_factory=dict)
    fixed: dict[str, Any] = field(default_factory=dict)

    platform = "carto"

    @property
    def label(self) -> str:
        return f"carto:{self.account_url}/{self.table}"

    @property
    def page_url(self) -> str:
        return f"{self.account_url}/api/v2/sql?q=SELECT * FROM {self.table} LIMIT 10"


Source = Union[SocrataSource, ArcGISSource, CkanSource, CartoSource]


@dataclass(frozen=True)
class City:
    key: str
    name: str
    state: str
    sources: tuple[Source, ...]
    fields: dict[str, FieldSpec]
    country: str = "US"
    notes: str = ""
