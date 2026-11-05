"""Offline tests: parsing, trade classification, normalization, filters, rollup, input schema sync."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.gen_input_schema import build  # noqa: E402
from src.cities import CITIES, CITY_BY_KEY  # noqa: E402
from src.contractors import contractor_key, rollup  # noqa: E402
from src.enrich import classify_trades  # noqa: E402
from src.filters import Filters  # noqa: E402
from src.main import InputError, parse_input  # noqa: E402
from src.normalize import OUTPUT_FIELDS, normalize  # noqa: E402
from src.parsing import normalize_phone, parse_date, parse_money, phone_in_text, property_type_from  # noqa: E402

TODAY = date(2026, 11, 5)


def test_parse_date_formats():
    assert parse_date("2026-11-04T00:00:00.000") == date(2026, 11, 4)
    assert parse_date("11/05/26") == date(2026, 11, 5)
    assert parse_date("2026-11-03T17:00:44") == date(2026, 11, 3)
    assert parse_date(1791864000000) == date(2026, 10, 13)  # ArcGIS epoch ms
    assert parse_date("2020-01-03") == date(2020, 1, 3)
    assert parse_date("2026-11-04T19:46:58Z") == date(2026, 11, 4)
    assert parse_date("") is None and parse_date(None) is None


def test_money_and_phone():
    assert parse_money("$2,000.00") == 2000.0
    assert parse_money("0") is None
    assert parse_money(282739) == 282739.0
    assert normalize_phone("9198286260") == "(919) 828-6260"
    assert normalize_phone("1-512-555-0199") == "(512) 555-0199"
    assert normalize_phone("0000000000") is None
    assert normalize_phone("123") is None
    assert phone_in_text("POC: PAMELA DANZY 615-992-1400") == "(615) 992-1400"
    assert phone_in_text("permit 2023033181") is None


def test_property_type():
    assert property_type_from("R") == "residential"
    assert property_type_from("Multi Family") == "residential"
    assert property_type_from("Non-Residential") == "commercial"
    assert property_type_from("Commercial") == "commercial"
    assert property_type_from("Building") is None


def test_trades():
    assert classify_trades("Install roof mounted solar PV system")[0] == "solar"
    assert "roofing" not in classify_trades("Install roof mounted solar PV system")
    assert classify_trades("Re-roof, tear off and replace shingles")[0] == "roofing"
    assert classify_trades("Upgrade service from 100 amps to 200 amps") == ["electrical"]
    assert classify_trades("Replace furnace and A/C condenser")[0] == "hvac"
    assert classify_trades("New SFR")[0] == "new_construction"
    assert classify_trades("Construct detached ADU in rear yard")[0] == "adu"
    assert classify_trades("Interior remodel of kitchen") == ["remodel"]
    assert classify_trades("") == []


def test_normalize_austin_like_row():
    city = CITY_BY_KEY["austin"]
    raw = {
        "permit_number": "2026-123456 BP", "permit_type_desc": "Building Permit", "permit_class": "R- 434 Addition & Alterations",
        "work_class": "Remodel", "description": "Reroof existing SFR, tear off and replace", "status_current": "Active",
        "permit_class_mapped": "Residential", "original_address1": "123 MAIN ST", "original_city": "AUSTIN",
        "original_zip": "78701", "latitude": "30.27", "longitude": "-97.74", "issue_date": "2026-11-03T00:00:00.000",
        "total_job_valuation": "18500", "contractor_company_name": "Lone Star Roofing LLC", "contractor_phone": "5125550199",
        "link": {"url": "https://abc.austintexas.gov/x"},
    }
    rec = normalize(raw, city, city.sources[0], TODAY)
    assert rec is not None
    assert set(rec) == set(OUTPUT_FIELDS)
    assert rec["record_id"] == "austin:2026-123456 BP"
    assert rec["primary_trade"] == "roofing"
    assert rec["property_type"] == "residential"
    assert rec["contractor_phone"] == "(512) 555-0199"
    assert rec["city"] == "Austin"
    assert rec["days_since_issued"] == 2
    assert rec["record_url"] == "https://abc.austintexas.gov/x"
    assert rec["lead_grade"] in ("HOT", "WARM")


def test_normalize_owner_builder_and_zip_padding():
    city = CITY_BY_KEY["miami-dade-county"]
    raw = {"PermitNumber": "2020020525", "PermitIssuedDate": "2026-11-01", "ContractorName": "OWNER", "PropertyAddress": "20415 NE 20 CT",
           "DetailDescriptionComments": "IMPACT WINDOWS", "CategoryDescription1": "WINDOWS", "__lat": 25.9, "__lon": -80.2}
    rec = normalize(raw, city, city.sources[0], TODAY)
    assert rec["owner_builder"] is True and rec["contractor_name"] is None
    assert rec["primary_trade"] == "windows_doors"
    assert rec["latitude"] == 25.9
    boston = CITY_BY_KEY["boston"]
    rec = normalize({"permitnumber": "E1", "issued_date": "2026-11-03T17:00:44", "zip": "2122"}, boston, boston.sources[0], TODAY)
    assert rec["zip"] == "02122"


def test_description_beats_generic_type_label():
    city = CITY_BY_KEY["philadelphia"]
    raw = {"permitnumber": "RP-1", "permitissuedate": "2026-11-04T10:00:00Z", "typeofwork": "ADDITION AND/OR ALTERATION",
           "approvedscopeofwork": "Installation of appliances with associated ductwork"}
    rec = normalize(raw, city, city.sources[0], TODAY)
    assert rec["primary_trade"] == "hvac" and "addition" in rec["trades"]


def test_austin_value_fallback():
    city = CITY_BY_KEY["austin"]
    raw = {"permit_number": "M1", "issue_date": "2026-11-01T00:00:00.000", "mechanical_valuation": "8200"}
    assert normalize(raw, city, city.sources[0], TODAY)["project_value"] == 8200.0


def test_normalize_requires_permit_number():
    city = CITY_BY_KEY["chicago"]
    assert normalize({"issue_date": "2026-11-01"}, city, city.sources[0], TODAY) is None


def test_chicago_contacts():
    city = CITY_BY_KEY["chicago"]
    raw = {"permit_": "B1", "issue_date": "2026-11-01T00:00:00.000", "contact_1_type": "OWNER", "contact_1_name": "JANE DOE",
           "contact_2_type": "CONTRACTOR-ELECTRICAL", "contact_2_name": "SPARKY INC", "contact_2_city": "CHICAGO"}
    rec = normalize(raw, city, city.sources[0], TODAY)
    assert rec["contractor_name"] == "SPARKY INC"
    assert rec["owner_name"] == "JANE DOE"
    assert rec["contractor_city"] == "CHICAGO"


def _rec(**kw):
    base = {"issue_date": "2026-11-01", "trades": ["roofing"], "zip": "78701", "project_value": 20000.0,
            "property_type": "residential", "lead_grade": "WARM", "lead_reasons": []}
    base.update(kw)
    return base


def test_filters():
    f = Filters(date_from=date(2026, 10, 1), date_to=date(2026, 11, 5), trades=frozenset({"roofing"}), zip_codes=("787",), min_value=10000)
    assert f.matches(_rec())
    assert not f.matches(_rec(issue_date="2026-09-30"))
    assert not f.matches(_rec(trades=["solar"]))
    assert not f.matches(_rec(zip="75201"))
    assert not f.matches(_rec(project_value=None))
    hot = Filters(date_from=date(2026, 10, 1), date_to=date(2026, 11, 5), min_grade="HOT")
    assert not hot.matches(_rec())
    phone = Filters(date_from=date(2026, 10, 1), date_to=date(2026, 11, 5), require_contact="phone")
    assert not phone.matches(_rec()) and phone.matches(_rec(contractor_phone="(512) 555-0199"))


def test_rollup():
    rows = rollup([
        {"city_key": "austin", "city": "Austin", "state": "TX", "contractor_name": "Lone Star Roofing LLC", "project_value": 10000.0,
         "trades": ["roofing"], "issue_date": "2026-11-01", "permit_number": "1", "contractor_phone": "(512) 555-0199"},
        {"city_key": "austin", "city": "Austin", "state": "TX", "contractor_name": "LONE STAR ROOFING, L.L.C.", "project_value": 5000.0,
         "trades": ["roofing"], "issue_date": "2026-11-03", "permit_number": "2"},
        {"city_key": "austin", "city": "Austin", "state": "TX", "contractor_name": None, "permit_number": "3"},
    ])
    assert len(rows) == 1
    r = rows[0]
    assert r["permit_count"] == 2 and r["total_project_value"] == 15000.0
    assert r["latest_issue_date"] == "2026-11-03" and r["contractor_phone"] == "(512) 555-0199"
    assert contractor_key("ABC Builders, Inc.") == contractor_key("abc builders")


def test_parse_input():
    cfg = parse_input({"cities": ["austin"], "states": ["FL"], "lastNDays": 7}, TODAY)
    keys = [c.key for c in cfg.cities]
    assert keys[0] == "austin" and "miami" in keys and "miami-dade-county" in keys
    assert cfg.filters.date_from == date(2026, 10, 30) and cfg.filters.date_to == TODAY
    assert len(parse_input({}, TODAY).cities) == len(CITIES)
    for bad in ({"cities": ["atlantis"]}, {"trades": ["juggling"]}, {"dateFrom": "2026-11-10", "dateTo": "2026-11-01"}):
        try:
            parse_input(bad, TODAY)
        except InputError:
            continue
        raise AssertionError(f"expected InputError for {bad}")


def test_registry_and_schema_in_sync():
    keys = [c.key for c in CITIES]
    assert len(keys) == len(set(keys)), "duplicate city keys"
    for c in CITIES:
        assert "permit_number" in c.fields and c.sources, c.key
    on_disk = json.loads((ROOT / ".actor" / "input_schema.json").read_text(encoding="utf-8"))
    assert on_disk == build(), "input_schema.json is stale: run python scripts/gen_input_schema.py"
