"""Turn a raw source row into the normalized permit record."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

from .enrich import classify_trades, score_lead
from .models import City, Source
from .parsing import (
    clean_str,
    get_value,
    iso,
    normalize_email,
    normalize_phone,
    parse_date,
    parse_float,
    parse_money,
    phone_in_text,
    property_type_from,
    valid_coord,
)

OUTPUT_FIELDS: tuple[str, ...] = (
    "record_type", "record_id", "city_key", "city", "state", "country",
    "permit_number", "permit_type", "permit_subtype", "work_class", "description", "status",
    "primary_trade", "trades", "property_type",
    "address", "zip", "latitude", "longitude",
    "applied_date", "issue_date", "expiration_date", "days_since_issued",
    "project_value",
    "contractor_name", "contractor_phone", "contractor_email", "contractor_license",
    "contractor_address", "contractor_city", "contractor_state", "contractor_zip",
    "owner_builder", "applicant_name", "owner_name", "description_phone",
    "lead_score", "lead_grade", "lead_reasons",
    "source_platform", "source_dataset", "record_url", "scraped_at",
)

_TEXT_FIELDS = (
    "permit_number", "permit_type", "permit_subtype", "work_class", "description", "status", "address",
    "city", "contractor_name", "contractor_license", "contractor_address", "contractor_city",
    "contractor_state", "applicant_name", "owner_name", "record_url",
)
_OWNER_BUILDER = re.compile(r"^(owner|home ?owner|owner[ /-]?builder|property owner|self)$", re.I)
_ZIP = re.compile(r"\b(\d{5})(?:-\d{4})?\b|\b([A-Z]\d[A-Z] ?\d[A-Z]\d)\b", re.I)
_MAX_DESCRIPTION = 1500


def _zip(value: Any, address: str | None) -> str | None:
    text = clean_str(value)
    if text:
        if text.isdigit() and len(text) < 5:  # numeric columns lose leading zeros (e.g. Boston 2122)
            text = text.zfill(5)
        match = _ZIP.search(text)
        if match:
            return (match[1] or match[2]).upper()
    if address:
        match = _ZIP.search(address)
        if match and match[1]:
            return match[1]
    return None


def normalize(raw: dict[str, Any], city: City, source: Source, today: date) -> dict[str, Any] | None:
    spec = {**city.fields, **source.fields}
    out: dict[str, Any] = {}

    for name in _TEXT_FIELDS:
        out[name] = clean_str(get_value(raw, spec.get(name)))
    if not out["permit_number"]:
        return None
    if out["description"] and len(out["description"]) > _MAX_DESCRIPTION:
        out["description"] = out["description"][:_MAX_DESCRIPTION] + "…"

    issue = parse_date(get_value(raw, spec.get("issue_date", source.date_field)))
    applied = parse_date(get_value(raw, spec.get("applied_date")))
    expires = parse_date(get_value(raw, spec.get("expiration_date")))

    lat = parse_float(get_value(raw, spec.get("latitude")))
    lon = parse_float(get_value(raw, spec.get("longitude")))
    if lat is None or lon is None:
        lat, lon = parse_float(raw.get("__lat")), parse_float(raw.get("__lon"))
    lat, lon = valid_coord(lat, lon)

    contractor = out["contractor_name"]
    owner_builder = bool(contractor and _OWNER_BUILDER.match(contractor))
    if owner_builder:
        contractor = None

    property_type = source.fixed.get("property_type") or property_type_from(get_value(raw, spec.get("property_type")))

    # The work description (and explicit trade hints) decide the primary trade; generic type labels such as
    # "Addition/Alteration" only fill in when the description says nothing recognizable.
    specific = classify_trades(out["description"], clean_str(get_value(raw, spec.get("_trade_hints"))))
    generic = classify_trades(out["permit_type"], out["permit_subtype"], out["work_class"])
    trades = specific + [t for t in generic if t not in specific]

    record: dict[str, Any] = {
        "record_type": "permit",
        "record_id": f"{city.key}:{out['permit_number']}",
        "city_key": city.key,
        "city": out["city"].title() if out["city"] and out["city"].isupper() else (out["city"] or city.name),
        "state": city.state,
        "country": city.country,
        "permit_number": out["permit_number"],
        "permit_type": out["permit_type"],
        "permit_subtype": out["permit_subtype"],
        "work_class": out["work_class"],
        "description": out["description"],
        "status": out["status"],
        "primary_trade": trades[0] if trades else "other",
        "trades": trades,
        "property_type": property_type,
        "address": out["address"],
        "zip": _zip(get_value(raw, spec.get("zip")), out["address"]),
        "latitude": lat,
        "longitude": lon,
        "applied_date": iso(applied),
        "issue_date": iso(issue),
        "expiration_date": iso(expires),
        "days_since_issued": (today - issue).days if issue else None,
        "project_value": parse_money(get_value(raw, spec.get("project_value"))),
        "contractor_name": contractor,
        "contractor_phone": normalize_phone(get_value(raw, spec.get("contractor_phone"))),
        "contractor_email": normalize_email(get_value(raw, spec.get("contractor_email"))),
        "contractor_license": out["contractor_license"] if not owner_builder else None,
        "contractor_address": out["contractor_address"],
        "contractor_city": out["contractor_city"],
        "contractor_state": out["contractor_state"],
        "contractor_zip": _zip(get_value(raw, spec.get("contractor_zip")), None),
        "owner_builder": owner_builder,
        "applicant_name": out["applicant_name"],
        "owner_name": out["owner_name"],
        "description_phone": phone_in_text(out["description"]),
        "source_platform": source.platform,
        "source_dataset": source.page_url,
        "record_url": out["record_url"],
        "scraped_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    score, grade, reasons = score_lead(record, today)
    record["lead_score"], record["lead_grade"], record["lead_reasons"] = score, grade, reasons
    return {k: record.get(k) for k in OUTPUT_FIELDS}
