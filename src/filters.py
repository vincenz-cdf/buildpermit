"""Client-side filters applied to normalized permit records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

_GRADE_RANK = {"COLD": 0, "WARM": 1, "HOT": 2}


@dataclass(frozen=True)
class Filters:
    date_from: date
    date_to: date
    trades: frozenset[str] = frozenset()
    keywords: tuple[str, ...] = ()
    zip_codes: tuple[str, ...] = ()
    min_value: float | None = None
    property_type: str = "any"  # any | residential | commercial
    require_contact: str = "none"  # none | contractor | phone | phoneOrEmail
    exclude_owner_builder: bool = False
    exclude_closed: bool = False
    min_grade: str = "COLD"

    def matches(self, rec: dict[str, Any]) -> bool:
        issue = rec.get("issue_date")
        if not issue or not (self.date_from.isoformat() <= issue <= self.date_to.isoformat()):
            return False
        if self.trades and not self.trades.intersection(rec.get("trades") or ()):
            return False
        if self.keywords:
            blob = " ".join(
                str(rec.get(k) or "") for k in ("permit_type", "permit_subtype", "work_class", "description", "contractor_name")
            ).lower()
            if not any(k in blob for k in self.keywords):
                return False
        if self.zip_codes:
            z = rec.get("zip") or ""
            if not any(z.startswith(p) for p in self.zip_codes):
                return False
        if self.min_value is not None and (rec.get("project_value") or 0) < self.min_value:
            return False
        if self.property_type != "any" and rec.get("property_type") != self.property_type:
            return False
        if self.require_contact == "contractor" and not rec.get("contractor_name"):
            return False
        if self.require_contact == "phone" and not (rec.get("contractor_phone") or rec.get("description_phone")):
            return False
        if self.require_contact == "phoneOrEmail" and not (
            rec.get("contractor_phone") or rec.get("contractor_email") or rec.get("description_phone")
        ):
            return False
        if self.exclude_owner_builder and rec.get("owner_builder"):
            return False
        if self.exclude_closed and "permit already closed/finaled" in (rec.get("lead_reasons") or []):
            return False
        if _GRADE_RANK.get(rec.get("lead_grade") or "COLD", 0) < _GRADE_RANK.get(self.min_grade, 0):
            return False
        return True
