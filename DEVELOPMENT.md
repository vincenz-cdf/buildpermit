# Development notes

## Layout

| Path | What it does |
| --- | --- |
| `src/cities.py` | Registry: every jurisdiction, its source(s) and the column mapping onto normalized fields |
| `src/adapters/` | One reader per platform (Socrata, ArcGIS, CKAN, CARTO), plus `http.py` retries |
| `src/normalize.py` | Raw row → normalized permit (dates, money, phones, geo, owner-builder, trades, score) |
| `src/enrich.py` | Trade rules and lead scoring |
| `src/filters.py` | Input filters applied to normalized permits |
| `src/collect.py` | Per-city fetch loop; one broken source never fails the run |
| `src/contractors.py` | Contractor summary rows |
| `src/state.py` | "Only new" memory (named key-value store `building-permit-leads-state`) |
| `src/main.py` | Input parsing, charging, run summary, health check |
| `scripts/gen_input_schema.py` | Builds `.actor/input_schema.json` from the registry |
| `tests/test_offline.py` | Offline tests (no network) |

## Local setup

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt pytest
.venv\Scripts\python.exe -m pytest -q tests
```

Run the Actor locally: put an input in `storage/key_value_stores/default/INPUT.json`, then
`.venv\Scripts\python.exe -m src`. Output lands in `storage/datasets/default/`.

## Secrets

Never commit credentials. The Actor reads them from environment variables, set in Apify Console under
**Actor → Settings → Environment variables** with **Secret** ticked:

| Variable | Use |
| --- | --- |
| `SOCRATA_APP_TOKEN` | Recommended. Raises Socrata rate limits. Create it at your Socrata profile → Developer settings → Create New App Token. |
| `SOCRATA_KEY_ID` / `SOCRATA_KEY_SECRET` | Optional alternative (HTTP basic auth), used only when no app token is set. |

If a token is rejected, the Actor logs a warning and continues anonymously. ArcGIS, CKAN and CARTO sources need no keys.

## Pricing (pay per event)

Configure in Console → Publication → Monetization:

| Event name | Suggested price | Charged when |
| --- | --- | --- |
| `permit` | $0.003 ($3 / 1,000) | Each permit row pushed |
| `contractor` | $0.01 | Each contractor summary row pushed |

The code charges through `Actor.push_data(..., charged_event_name=...)`, which stops at the user's maximum cost per run.
Health-check runs push nothing and are not charged.

## Adding a city

1. Find the dataset (Socrata: `api.us.socrata.com/api/catalog/v1?q=building permits`; ArcGIS: search
   `arcgis.com/sharing/rest/search` for Feature Services; CKAN: `/api/3/action/package_search`).
2. Check its columns and that the newest issue date is recent.
3. Add a `City(...)` to `src/cities.py` mapping columns to normalized fields.
4. `python scripts/gen_input_schema.py`, then run the tests and a health check for that city:
   `{"healthCheck": true, "cities": ["<key>"]}`.
5. Add the city's row to the coverage table in `README.md`.

## Maintenance

Schedule a weekly run with `{"healthCheck": true}`. The `HEALTH` record lists any source that errors, is empty,
or whose newest permit is older than 14 days. Known watch items:

- **Washington DC** publishes one layer per year (`Building Permits - {year}`); the Actor picks yearly layers by
  name, so January needs no change unless DC renames them.
- **Saint Paul** was removed: its public layer stopped updating in June 2025.
- **Dallas** stores dates as text, so it is filtered after download (newest rows first by row id).

## Publish

```bash
npm install -g apify-cli
apify login
apify push
```
