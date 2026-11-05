"""Value parsing helpers and field-spec builders shared by the city registry and the normalizer."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, datetime, timezone
from typing import Any

from .models import FieldSpec

_EMPTY = {"", "null", "none", "n/a", "na", "nan", "-", "--", "0000000000", "not listed"}
_WS = re.compile(r"\s+")


def clean_str(value: Any) -> str | None:
    """Strip, collapse whitespace and turn placeholder values into None."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return None
    text = _WS.sub(" ", str(value)).strip()
    if text.lower() in _EMPTY:
        return None
    return text


def get_value(raw: dict[str, Any], spec: FieldSpec | None) -> Any:
    if spec is None:
        return None
    if callable(spec):
        return spec(raw)
    if isinstance(spec, tuple):
        for name in spec:
            value = raw.get(name)
            if clean_str(value) is not None:
                return value
        return None
    return raw.get(spec)


def join(*names: str, sep: str = " ") -> Callable[[dict[str, Any]], str | None]:
    """Field spec that joins several raw columns, skipping empty ones."""

    def _join(raw: dict[str, Any]) -> str | None:
        parts = [clean_str(raw.get(n)) for n in names]
        text = sep.join(p for p in parts if p)
        return text or None

    return _join


def geo(field_name: str, axis: str) -> Callable[[dict[str, Any]], float | None]:
    """Read latitude/longitude out of a Socrata ``location`` or ``point`` column."""

    def _geo(raw: dict[str, Any]) -> float | None:
        value = raw.get(field_name)
        if not isinstance(value, dict):
            return None
        if "coordinates" in value:  # GeoJSON point: [lon, lat]
            coords = value.get("coordinates") or []
            if len(coords) >= 2:
                return coords[1] if axis == "lat" else coords[0]
            return None
        return value.get("latitude" if axis == "lat" else "longitude")

    return _geo


def contact_of_type(prefix: str, count: int, type_contains: str, attr: str = "name") -> Callable[[dict[str, Any]], str | None]:
    """Chicago-style numbered contacts: contact_1_type/contact_1_name ... contact_N_*."""

    needle = type_contains.upper()

    def _contact(raw: dict[str, Any]) -> str | None:
        for i in range(1, count + 1):
            ctype = clean_str(raw.get(f"{prefix}_{i}_type")) or ""
            if needle in ctype.upper():
                value = clean_str(raw.get(f"{prefix}_{i}_{attr}"))
                if value:
                    return value
        return None

    return _contact


# ---------------------------------------------------------------- dates

_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %I:%M:%S %p",
    "%Y/%m/%d",
)


def parse_date(value: Any) -> date | None:
    """Parse ISO strings, US-style strings and ArcGIS epoch milliseconds into a date."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        # ArcGIS dates are epoch milliseconds (UTC). Local midnight lands on the same UTC date for US zones.
        try:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date()
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "").split("+")[0]
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # Last resort: leading ISO date.
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        try:
            return date(int(match[1]), int(match[2]), int(match[3]))
        except ValueError:
            return None
    return None


def iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


# ---------------------------------------------------------------- numbers, phones, emails

_MONEY_JUNK = re.compile(r"[^0-9.\-]")


def parse_money(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = _MONEY_JUNK.sub("", str(value))
        if text in ("", ".", "-"):
            return None
        try:
            number = float(text)
        except ValueError:
            return None
    if number <= 0 or number > 5e10:  # 0 means "not reported"; anything above $50B is a data-entry error
        return None
    return round(number, 2)


def parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


_PHONE_DIGITS = re.compile(r"\D")


def normalize_phone(value: Any) -> str | None:
    """Return a US/Canada phone number as (XXX) XXX-XXXX, or None if it is not one."""
    text = clean_str(value)
    if not text:
        return None
    digits = _PHONE_DIGITS.sub("", text)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10 or digits[0] in "01" or len(set(digits)) == 1:
        return None
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


_PHONE_IN_TEXT = re.compile(r"(?<!\d)\(?([2-9]\d{2})\)?[\s.\-]([2-9]\d{2})[\s.\-](\d{4})(?!\d)")


def phone_in_text(text: str | None) -> str | None:
    if not text:
        return None
    match = _PHONE_IN_TEXT.search(text)
    if not match:
        return None
    return f"({match[1]}) {match[2]}-{match[3]}"


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)


def normalize_email(value: Any) -> str | None:
    text = clean_str(value)
    if not text:
        return None
    text = text.lower()
    return text if _EMAIL.match(text) else None


def valid_coord(lat: float | None, lon: float | None) -> tuple[float | None, float | None]:
    if lat is None or lon is None:
        return None, None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (abs(lat) < 0.01 and abs(lon) < 0.01):
        return None, None
    return round(lat, 7), round(lon, 7)


def property_type_from(value: Any) -> str | None:
    """Map the many ways cities write residential/commercial onto two values."""
    text = (clean_str(value) or "").lower()
    if not text:
        return None
    # Commercial first: "Non-Residential" contains "resid".
    if text in ("c", "com", "comm") or "commerc" in text or "non-res" in text or "nonres" in text or "non res" in text:
        return "commercial"
    residential_words = ("resid", "1-2fam", "single", "dwelling", "family", "duplex", "townho", "apartment", "condo")
    if text in ("r", "res") or any(w in text for w in residential_words):
        return "residential"
    return None
