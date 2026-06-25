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
   Airflow scheduler (slim) ──schedule */30──▶ Redis broker (CeleryExecutor)
                                                    │ routes each task to its queue
        ┌───────────────┬───────────────┬──────────┴────────┐
        ▼               ▼               ▼                    ▼
   ┌─────────┐    ┌─────────┐    ┌──────┐           ┌───────────────┐
   │ prepare │───▶│ extract │───▶│ load │──────────▶│ transform     │
   │ worker  │    │ worker  │    │worker│           │ worker (dbt)  │
   └─────────┘    └─────────┘    └──────┘           └───────────────┘
    raw schema   /data (JSON)    raw.stations        staging → marts
    + watermark   ◀── shared volume ──▶ raw.fuel_prices  dim_stations
                                       raw.pipeline_runs fct_fuel_prices
                                                              │
                                                              ▼
                                                    ┌──────────────────┐
                                                    │  Streamlit App   │
                                                    │  :8501           │
                                                    └──────────────────┘
```

Each pipeline stage runs on its **own Airflow worker image** under CeleryExecutor, routed by queue. The scheduler/webserver stay slim (no stage dependencies), and a fault in one stage is isolated to its worker. Celery is used instead of launching containers per task so the stack runs on any host without a Docker socket.

**Prepare** — creates the `raw` schema, opens a pipeline run, and writes the incremental watermark to the shared volume. The load worker owns all database access.

**Extract** — authenticates with the Fuel Finder API via OAuth 2.0, fetches stations and prices in paginated batches, writes JSON to the shared volume (no database access).

**Load** — upserts station metadata and appends fuel price records into the `raw` PostgreSQL schema, then completes the pipeline run. Supports incremental runs: the first run fetches everything; later runs fetch only records changed since the last completed run, using `raw.pipeline_runs` as the watermark.

**Transform** — dbt materialises staging views, an intermediate join layer, and mart tables (`dim_stations`, `fct_fuel_prices`) queried by the app.

**App** — Streamlit dashboard with a UK-wide price heatmap (mean-centred diverging colour scale) and a postcode/address search returning nearby stations sorted by price.

---

## Stack

| Layer | Technology |
|---|---|
| Orchestration | Apache Airflow 2.10 (CeleryExecutor, per-stage workers) |
| Broker | Redis 7 |
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
uv run fnme-cli --address "London, UK" --radius 5 --sort distance
```

Sort options: `distance`, `e10`, `e5`, `b7s`

Full options: `uv run fnme-cli --help`

## AI Disclaimer
Claude Code was used to assist development. Whilst I maintain and review the code, I make the final decisions in regards to the direction of the project.
