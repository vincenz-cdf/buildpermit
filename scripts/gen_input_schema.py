"""Regenerate .actor/input_schema.json from the city registry and trade list.

Run after adding a city:  python scripts/gen_input_schema.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.cities import CITIES  # noqa: E402
from src.enrich import TRADES  # noqa: E402

TRADE_TITLES = {
    "solar": "Solar / PV / battery", "roofing": "Roofing", "pool": "Pool & spa", "adu": "ADU / accessory dwelling",
    "new_construction": "New construction", "addition": "Addition", "demolition": "Demolition", "hvac": "HVAC / mechanical",
    "electrical": "Electrical", "plumbing": "Plumbing & gas", "fire_protection": "Fire alarm & sprinkler",
    "windows_doors": "Windows & doors", "siding": "Siding / stucco / facade", "fence_deck": "Fence, deck, patio, porch",
    "foundation": "Foundation & structural", "elevator": "Elevator", "sign": "Signs & awnings", "remodel": "Remodel / alteration / repair",
}


def build() -> dict:
    states = sorted({c.state for c in CITIES})
    return {
        "title": "Building Permit Leads",
        "type": "object",
        "schemaVersion": 1,
        "properties": {
            "cities": {
                "title": "Cities / counties",
                "type": "array",
                "description": "Pick one or more jurisdictions. Leave empty (and leave States empty) to search all of them.",
                "editor": "select",
                "items": {
                    "type": "string",
                    "enum": [c.key for c in CITIES],
                    "enumTitles": [f"{c.name}, {c.state}" for c in CITIES],
                },
                "prefill": ["austin", "chicago"],
            },
            "states": {
                "title": "States / provinces",
                "type": "array",
                "description": "Adds every supported jurisdiction in these states, e.g. TX adds Austin, Dallas, San Antonio and Collin County.",
                "editor": "select",
                "items": {"type": "string", "enum": states},
            },
            "lastNDays": {
                "title": "Issued in the last N days",
                "type": "integer",
                "description": "Ignored when 'Issued from' is set. Cities publish with a 1-7 day lag, so 7+ days is safest for daily schedules.",
                "minimum": 1,
                "maximum": 3650,
                "default": 30,
            },
            "dateFrom": {
                "title": "Issued from",
                "type": "string",
                "description": "First issue date to include (YYYY-MM-DD). Overrides 'last N days'.",
                "editor": "datepicker",
            },
            "dateTo": {
                "title": "Issued until",
                "type": "string",
                "description": "Last issue date to include (YYYY-MM-DD). Defaults to today.",
                "editor": "datepicker",
            },
            "trades": {
                "title": "Trades",
                "type": "array",
                "description": "Keep permits whose work matches any of these trades. Leave empty for all permits.",
                "editor": "select",
                "items": {"type": "string", "enum": list(TRADES), "enumTitles": [TRADE_TITLES[t] for t in TRADES]},
                "sectionCaption": "Filters",
            },
            "keywords": {
                "title": "Keywords",
                "type": "array",
                "description": "Keep permits whose type, description or contractor contains any of these words (case-insensitive).",
                "editor": "stringList",
            },
            "zipCodes": {
                "title": "ZIP / postal codes",
                "type": "array",
                "description": "Keep permits in these ZIP codes. A prefix works too: '787' matches all of 787xx.",
                "editor": "stringList",
            },
            "minProjectValue": {
                "title": "Minimum project value ($)",
                "type": "integer",
                "description": "Drops permits below this value, and permits from cities that do not publish a value.",
                "minimum": 0,
            },
            "propertyType": {
                "title": "Property type",
                "type": "string",
                "editor": "select",
                "enum": ["any", "residential", "commercial"],
                "enumTitles": ["Any", "Residential only", "Commercial only"],
                "default": "any",
            },
            "requireContact": {
                "title": "Require contact details",
                "type": "string",
                "editor": "select",
                "description": "Only keep permits that name a contractor, or that have a phone number.",
                "enum": ["none", "contractor", "phone", "phoneOrEmail"],
                "enumTitles": ["No requirement", "Contractor name", "Phone number", "Phone or email"],
                "default": "none",
            },
            "excludeOwnerBuilder": {
                "title": "Exclude owner-builder permits",
                "type": "boolean",
                "description": "Skip permits where the owner is doing the work themselves.",
                "default": False,
            },
            "excludeClosed": {
                "title": "Exclude finaled / closed / expired permits",
                "type": "boolean",
                "default": False,
            },
            "minLeadGrade": {
                "title": "Minimum lead grade",
                "type": "string",
                "editor": "select",
                "enum": ["COLD", "WARM", "HOT"],
                "enumTitles": ["All (COLD and up)", "WARM and HOT", "HOT only"],
                "default": "COLD",
            },
            "outputMode": {
                "title": "Output",
                "type": "string",
                "editor": "select",
                "description": "Permits: one row per permit. Contractors: one row per contractor with permit count, value and trades. Both: permits plus contractor rows.",
                "enum": ["permits", "contractors", "both"],
                "enumTitles": ["Permits", "Contractor summary", "Both"],
                "default": "permits",
                "sectionCaption": "Output & scheduling",
            },
            "onlyNew": {
                "title": "Only permits not delivered before",
                "type": "boolean",
                "description": "Remembers delivered permits between runs, so scheduled runs only return (and charge for) new ones.",
                "default": False,
            },
            "stateKey": {
                "title": "Memory name for 'only new'",
                "type": "string",
                "description": "Use a different name per schedule, so each schedule remembers its own permits.",
                "default": "default",
            },
            "maxResultsPerCity": {
                "title": "Max permits per city",
                "type": "integer",
                "description": "Newest permits first. Also caps the permits used for the contractor summary.",
                "minimum": 1,
                "maximum": 100000,
                "default": 500,
            },
            "maxResults": {
                "title": "Max permits in total",
                "type": "integer",
                "description": "0 = no overall limit (the per-city limit still applies).",
                "minimum": 0,
                "default": 0,
            },
            "includeRaw": {
                "title": "Include raw source record",
                "type": "boolean",
                "description": "Adds the original row from the city's portal under 'raw'.",
                "default": False,
            },
            "socrataAppToken": {
                "title": "Socrata app token (optional)",
                "type": "string",
                "description": "Your own free Socrata app token for higher rate limits. Not needed for normal use.",
                "isSecret": True,
                "sectionCaption": "Advanced",
            },
            "healthCheck": {
                "title": "Health check only",
                "type": "boolean",
                "description": "Checks that each selected source answers and how recent its newest permit is. Writes the HEALTH record; returns no permits.",
                "default": False,
            },
        },
    }


if __name__ == "__main__":
    out = ROOT / ".actor" / "input_schema.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
