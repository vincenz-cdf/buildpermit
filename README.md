# Building Permit Leads: Contractors, Phones & Trades (US + Canada)

Get **newly issued building permits** from **31 official city and county open-data portals** in one run, already
sorted into trades (roofing, solar, HVAC, pools, ADUs, new construction...), scored as HOT / WARM / COLD leads, and
with the **contractor's name, phone, email and license** wherever the city publishes them.

Built for roofers, solar installers, HVAC and pool companies, building-material suppliers, insurance and
home-services marketers who want a fresh list of real projects every morning.

## Why this Actor

- **31 jurisdictions, 4 data platforms.** Socrata, ArcGIS, CKAN and CARTO portals, not just one. Includes cities
  most permit scrapers skip: Raleigh, Nashville, Columbus, Cleveland, Detroit, Baltimore, Washington DC, Miami,
  Miami-Dade, Philadelphia, Boston, San Antonio, Collin County TX, Calgary and Edmonton.
- **Many cities per run.** Pick cities, or whole states (e.g. `TX` adds Austin, Dallas, San Antonio and Collin County).
- **One clean schema.** Every city's columns are mapped to the same fields, dates are `YYYY-MM-DD`, values are
  numbers, phones are `(512) 555-0199`.
- **Trade categories on every permit**, from the work description first, so "Addition/Alteration" boilerplate
  doesn't hide what the job actually is.
- **Lead score** (0-100) and grade, with the reasons spelled out.
- **Only new permits** mode for daily schedules: you never pay twice for the same permit.
- **Contractor summary**: one row per contractor with permit count, total value, main trades and contact details.
- **Never fails because one city is down.** Other cities still deliver, and `RUN_SUMMARY` says what happened.
- **Honest coverage.** The table below shows exactly which fields each city publishes.

## What you get per permit

| Field | Example |
| --- | --- |
| `lead_grade`, `lead_score`, `lead_reasons` | `HOT`, `74`, `["issued in the last 7 days", "contractor phone", ...]` |
| `issue_date`, `applied_date`, `days_since_issued` | `2026-11-03`, `2026-10-21`, `2` |
| `primary_trade`, `trades` | `roofing`, `["roofing", "remodel"]` |
| `permit_number`, `permit_type`, `work_class`, `description`, `status` | `BLDR-012345-2026`, `Building`, `Alterations/Repairs`, `Removing and replacing roof...`, `Issued` |
| `address`, `city`, `state`, `zip`, `latitude`, `longitude` | `123 Main St`, `Raleigh`, `NC`, `27609`, ... |
| `property_type` | `residential` / `commercial` |
| `project_value` | `18500` |
| `contractor_name`, `contractor_phone`, `contractor_email`, `contractor_license`, `contractor_address` | `Power Home Remodeling`, `(610) 874-5000`, ... |
| `owner_builder`, `owner_name`, `applicant_name` | `false`, ... |
| `description_phone` | A phone number written inside the permit description (common in Nashville) |
| `record_url`, `source_dataset`, `source_platform` | Link to the permit on the city's site when available |

Trades: `solar`, `roofing`, `pool`, `adu`, `new_construction`, `addition`, `demolition`, `hvac`, `electrical`,
`plumbing`, `fire_protection`, `windows_doors`, `siding`, `fence_deck`, `foundation`, `elevator`, `sign`, `remodel`
(and `other`).

## Coverage

✅ = filled on most permits · ◐ = filled on some permits · — = the city does not publish it.
Measured on a live 7-day sample (November 2026; Montgomery County from its published columns, as its feed lagged
that week). Contact fields appear only where the city itself publishes them.

| Key | Jurisdiction | Value | Contractor | Phone | Email | License | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `anaheim` | Anaheim, CA | ✅ | ✅ | ✅ | — | — | — |
| `austin` | Austin, TX | ◐ | ✅ | ✅ | — | — | — |
| `baltimore` | Baltimore, MD | ✅ | — | — | — | — | — |
| `baton-rouge` | East Baton Rouge Parish, LA | ◐ | ◐ | — | — | — | ✅ |
| `boston` | Boston, MA | ✅ | — | — | — | — | — |
| `calgary` | Calgary, AB | ✅ | ✅ | — | — | — | — |
| `cambridge-ma` | Cambridge, MA | ✅ | ✅ | — | — | — | — |
| `chicago` | Chicago, IL | ✅ | ✅ | — | — | — | ✅ |
| `cincinnati` | Cincinnati, OH | ✅ | ✅ | — | — | — | — |
| `cleveland` | Cleveland, OH | ✅ | ✅ | — | — | ✅ | — |
| `collin-county-tx` | Collin County, TX (Plano, Frisco, McKinney...) | ◐ | ✅ | — | — | — | ✅ |
| `columbus` | Columbus, OH | ◐ | ✅ | — | — | — | — |
| `dallas` | Dallas, TX | — | — | — | — | — | — |
| `detroit` | Detroit, MI | ✅ | — | — | — | — | — |
| `edmonton` | Edmonton, AB | ✅ | — | — | — | — | — |
| `los-angeles` | Los Angeles, CA | ✅ | — | — | — | — | — |
| `marin-county` | Marin County, CA | ✅ | ✅ | — | — | ◐ | — |
| `mesa` | Mesa, AZ | ✅ | ◐ | ◐ | ◐ | ◐ | — |
| `miami` | Miami (city), FL | ✅ | ✅ | — | — | — | — |
| `miami-dade-county` | Miami-Dade County, FL | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| `montgomery-county-md` | Montgomery County, MD | ✅ | — | — | — | — | — |
| `nashville` | Nashville, TN | ✅ | ✅ | ◐ * | — | — | — |
| `new-orleans` | New Orleans, LA | ✅ | ✅ | — | — | — | ✅ |
| `norfolk` | Norfolk, VA | ✅ | — | — | — | — | — |
| `nyc` | New York City, NY | ✅ | ✅ | — | — | ✅ | ✅ |
| `philadelphia` | Philadelphia, PA | — | ✅ | — | — | — | ✅ |
| `raleigh` | Raleigh, NC | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| `san-antonio` | San Antonio, TX | ◐ | — | — | — | — | — |
| `san-francisco` | San Francisco, CA | ✅ | — | — | — | — | — |
| `seattle` | Seattle, WA | ✅ | — | — | — | — | — |
| `washington-dc` | Washington, DC | — | — | — | — | — | ✅ |

\* Nashville phones come from `description_phone` (a number written in the permit text).

Want another city? Open an issue with a link to its open-data permit dataset.

## Examples

**Roofing and solar leads in Texas from the last 7 days, contractor known:**

```json
{
  "states": ["TX"],
  "lastNDays": 7,
  "trades": ["roofing", "solar"],
  "requireContact": "contractor"
}
```

**Daily schedule: only new HOT/WARM permits over $50k in Raleigh and Nashville:**

```json
{
  "cities": ["raleigh", "nashville"],
  "lastNDays": 7,
  "minProjectValue": 50000,
  "minLeadGrade": "WARM",
  "onlyNew": true,
  "stateKey": "nc-tn-daily"
}
```

**Most active pool and ADU contractors in Los Angeles, Anaheim and Marin over 90 days:**

```json
{
  "cities": ["los-angeles", "anaheim", "marin-county"],
  "lastNDays": 90,
  "trades": ["pool", "adu"],
  "outputMode": "contractors",
  "maxResultsPerCity": 5000
}
```

## Good to know

- **Freshness:** cities publish with a 1-7 day lag (NYC and Montgomery County tend to be the slowest). For daily
  schedules use `lastNDays: 7` with `onlyNew: true`: you get each permit once, as soon as it appears.
- **Newest first:** results are newest-first per city, and `maxResultsPerCity` stops at that many matches.
- **Filters run after download** for most fields, so very narrow filters over long date ranges scan more rows. The
  run summary shows rows scanned per city.
- **Owner-builder permits** are flagged with `owner_builder: true` and can be excluded.
- **Run summary:** every run writes `RUN_SUMMARY` to the key-value store with matched/scanned counts and any source
  errors per city.
- **Health check:** run with `healthCheck: true` to see how recent each source's newest permit is.

## Data and responsible use

All data comes from official government open-data portals (public records). A permit shows that work was
approved, not that it has started or that a contractor is still needed. Names and phone numbers are as published
by the city and are not verified. If you contact people from this data, you are responsible for following
telemarketing, email and privacy rules that apply to you (for example TCPA, CAN-SPAM, do-not-call lists and
state privacy laws).
