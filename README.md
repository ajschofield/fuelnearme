# FuelNearMe
**A full UK fuel price ELT pipeline that visualises data from the Fuel Finder public API, scheduled every 30 minutes via Airflow**

FuelNearMe is a full ELT pipeline that continuously ingests UK petrol station and fuel price data from the [Fuel Finder API](https://www.developer.fuel-finder.service.gov.uk/public-api), loads it into PostgreSQL, transforms it with dbt, and serves it through a Streamlit interface. The project originally began as a CLI tool, which is still available for use - the only
difference is that it uses the CSV data available as an alternative for the service.

As per the documentation, price updates submitted by fuel stations are reflected
on the platform within 30 minutes - the Airflow scheduler also follows this
timeframe.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                Apache Airflow (*/30 * * * *)        │
│                                                     │
│   ┌─────────┐     ┌──────┐     ┌───────────────┐    │
│   │ extract │────▶│ load │────▶│ transform     │    │
│   │ Python  │     │Python│     │ (dbt build)   │    │
│   └─────────┘     └──────┘     └───────────────┘    │
└─────────────────────────────────────────────────────┘
        │                 │               │
        ▼                 ▼               ▼
   /tmp (JSON)       raw schema      staging / marts
                    raw.stations     dim_stations
                  raw.fuel_prices    fct_fuel_prices
                 raw.pipeline_runs

                                         │
                                         ▼
                               ┌──────────────────┐
                               │  Streamlit App   │
                               │  :8501           │
                               └──────────────────┘
```

**Extract** — authenticates with the Fuel Finder API via OAuth 2.0, fetches stations and prices in paginated batches, writes JSON to a shared temp directory.

**Load** — upserts station metadata and appends fuel price records into the `raw` PostgreSQL schema. Supports incremental runs: on the first run all data is fetched; on subsequent runs only records changed since the last completed run are fetched, using `raw.pipeline_runs` as the watermark.

**Transform** — dbt materialises staging views, an intermediate join layer, and mart tables (`dim_stations`, `fct_fuel_prices`) queried by the app.

**App** — Streamlit dashboard with a UK-wide price heatmap (mean-centred diverging colour scale) and a postcode/address search returning nearby stations sorted by price.

---

## Stack

| Layer | Technology |
|---|---|
| Orchestration | Apache Airflow 2.10 (LocalExecutor) |
| Extract / Load | Python 3.12 |
| Transform | dbt-postgres 1.10 |
| Database | PostgreSQL 16 |
| App | Streamlit + pydeck |
| Infrastructure | Docker Compose |

---

## Prerequisites

- Docker Engine
- API credentials from the [developer portal](https://www.developer.fuel-finder.service.gov.uk)
  - Requires a GOV.UK One Login

---

## Quick Start

**1. Configure credentials**

Create a `.env` file in the project root:

```
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
```

**2. Build and start**

```bash
docker compose up --build
```

**3. Access**

| Service | URL | Credentials |
|---|---|---|
| Airflow UI | http://localhost:8080 | admin / admin |
| Streamlit app | http://localhost:8501 | — |

The pipeline triggers automatically every 30 minutes. You can also trigger it manually from the Airflow UI.

## CLI

The original CLI tool runs independently from the ELT pipeline. There are no
API credentials required to use this as it ingests the CSV copy available
from the Fuel Finder website.

```bash
uv sync
uv run fnme --address "London, UK" --radius 5 --sort distance
```

Sort options: `distance`, `e10`, `e5`, `b7s`

Full options: `uv run fnme --help`

## AI Disclaimer
Claude Code was used to assist development. Whilst I maintain and review the code, I make the final decisions in regards to the direction of the project.
