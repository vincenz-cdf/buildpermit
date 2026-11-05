"""Trade classification and lead scoring. Rule-based so results are explainable and stable."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

# Ordered by priority: the first matching trade becomes ``primary_trade``.
TRADE_RULES: tuple[tuple[str, str], ...] = (
    ("solar", r"\bsolar\b|photovoltaic|\bpv\b|\bpv[- ]system|battery storage|powerwall"),
    ("roofing", r"\bre-?roof|\broof(?![- ]?(mount|top))(ing|s)?\b|shingle|tear[- ]?off"),
    ("pool", r"\bpools?\b|\bspas?\b|swimming|hot tub"),
    ("adu", r"\badu\b|\bdadu\b|accessory dwelling|granny flat|casita|backyard cottage|in-?law unit"),
    ("new_construction", r"\bnew (construction|building|bldg|single|sfr|sfd|dwelling|residence|home|house|commercial|structure|duplex|townhouse|multi)|\bconstruct (a )?new|\bnew build|\berect"),
    ("addition", r"\baddition\b|\badd (a |an )?(room|story|bedroom|bathroom|garage|second)"),
    ("demolition", r"\bdemo(lition|lish)?\b|\bwreck|\braze\b"),
    ("hvac", r"\bhvac\b|mechanical|furnace|air[- ]?condition|\ba/c\b|heat pump|\bducts?(work)?\b|mini[- ]?split|\bboiler|condens(er|ing unit)|\brtu\b|rooftop unit"),
    ("electrical", r"electric|\bwiring\b|\brewire|service upgrade|\bpanel\b|\bamps?\b|ev charg|generator|receptacle|lighting"),
    ("plumbing", r"plumb|water heater|\bsewer|gas (line|piping)|backflow|re-?pip|water (line|service)|\bdrain"),
    ("fire_protection", r"fire (alarm|sprinkler|suppression|protection)|\bsprinkler"),
    ("windows_doors", r"\bwindows?\b|\bdoors?\b|storefront|glazing|\bshutters?\b"),
    ("siding", r"\bsiding\b|stucco|fa[cç]ade|cladding"),
    ("fence_deck", r"\bfenc(e|ing)\b|\bdecks?\b|\bpatio|pergola|\bporch|carport|retaining wall"),
    ("foundation", r"foundation|underpin|\bpiers?\b|structural repair"),
    ("elevator", r"elevator|escalator|wheelchair lift"),
    ("sign", r"\bsigns?\b|signage|billboard|awning"),
    ("remodel", r"remodel|renovat|alteration|\balter\b|interior (finish|work)|tenant improvement|\bt\.?i\.?\b|build[- ]?out|\brepair"),
)
TRADES: tuple[str, ...] = tuple(name for name, _ in TRADE_RULES)
_COMPILED = tuple((name, re.compile(pattern, re.I)) for name, pattern in TRADE_RULES)

_CLOSED_STATUS = re.compile(r"final|closed|complete|expired|void|cancel|withdrawn|revoked|denied|refused", re.I)
_OPEN_STATUS = re.compile(r"issued|active|open|approved|inspection", re.I)


def classify_trades(*texts: str | None) -> list[str]:
    blob = " | ".join(t for t in texts if t)
    if not blob:
        return []
    return [name for name, rx in _COMPILED if rx.search(blob)]


def score_lead(record: dict[str, Any], today: date) -> tuple[int, str, list[str]]:
    """0-100 score from freshness, project size, reachable contact and permit status."""
    score = 0
    reasons: list[str] = []

    days = record.get("days_since_issued")
    if days is not None:
        if days <= 7:
            score += 30
            reasons.append("issued in the last 7 days")
        elif days <= 30:
            score += 20
            reasons.append("issued in the last 30 days")
        elif days <= 90:
            score += 10

    value = record.get("project_value")
    if value:
        if value >= 250_000:
            score += 25
            reasons.append("project value $250k+")
        elif value >= 50_000:
            score += 18
            reasons.append("project value $50k+")
        elif value >= 10_000:
            score += 10
        else:
            score += 4

    if record.get("contractor_phone"):
        score += 20
        reasons.append("contractor phone")
    elif record.get("description_phone"):
        score += 10
        reasons.append("phone in description")
    if record.get("contractor_email"):
        score += 8
        reasons.append("contractor email")
    if record.get("contractor_name"):
        score += 5
    if record.get("contractor_license"):
        score += 4

    trade = record.get("primary_trade")
    if trade in ("new_construction", "adu", "addition", "solar", "roofing", "pool"):
        score += 8
        reasons.append(f"high-intent trade: {trade}")

    status = record.get("status") or ""
    if status and _CLOSED_STATUS.search(status):
        score -= 15
        reasons.append("permit already closed/finaled")
    elif status and _OPEN_STATUS.search(status):
        score += 3

    score = max(0, min(100, score))
    grade = "HOT" if score >= 60 else "WARM" if score >= 35 else "COLD"
    return score, grade, reasons
