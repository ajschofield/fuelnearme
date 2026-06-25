# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A monorepo containing **two independent products** that share *no* Python code:

1. **`fnme` CLI** (`fnme/` package) — the original tool. Reads the **CSV** copy of fuel data from the Fuel Finder website, needs **no API credentials**. Entry point: `fnme.cli:main`.
2. **ELT pipeline** (`extract/`, `load/`, `transform/`, `dags/`, `app/`) — continuously ingests the **authenticated Fuel Finder API**, loads to Postgres, transforms with dbt, serves via Streamlit. This is the current focus of development.

The two halves use different data sources and import nothing from each other. Changes to one do not affect the other.

## Commands

Tooling is **uv** (not pip/poetry). The dev dependency group installs test/lint tooling.

```bash
uv sync                       # install deps + dev group
uv run pytest                 # full test suite
uv run pytest tests/core/test_geo.py            # one file
uv run pytest tests/core/test_geo.py::test_name # one test
uv run pytest --cov=fnme --cov=extract --cov=load --cov=dags --cov=app --cov-report=term-missing
uv run ruff check             # lint
uv run ruff format            # format
uv run fnme-cli --address "London, UK" --radius 5 --sort distance   # run the CLI
```

The whole ELT stack runs under Docker Compose:

```bash
docker compose up --build     # postgres, redis, airflow (init/scheduler/webserver + 3 workers), app
```

- Requires a root `.env` with `CLIENT_ID` / `CLIENT_SECRET` (Fuel Finder API). The CLI does **not** need these.
- **Prod overlay**: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up` swaps plaintext env for file-based Docker secrets (`./secrets/*.txt`, gitignored). Code reads them via `read_secret(name)` — `{name}_FILE` wins over `{name}` — defined per package (extract/load/app) to keep the worker images self-contained.
- Airflow UI: http://localhost:8080 (admin/admin). Streamlit: http://localhost:8501.
- **Host Postgres port is `5433`** (mapped to container `5432`) to avoid clashing with a local Postgres.
- Some `tests/load/` tests use **testcontainers** and need a running Docker daemon.

## ELT data flow

`prepare → extract → load → transform`, orchestrated by Airflow on a `*/30 * * * *` schedule (matches the API's 30-minute price-update guarantee). See `dags/fuelnearme_pipeline.py`.

**Each stage runs on its own Airflow worker image under CeleryExecutor**, routed by `queue=` (Redis broker). The scheduler/webserver use the **plain `apache/airflow` image** — no stage deps or code. Each worker image (`extract/Dockerfile`, `load/Dockerfile`, `transform/Dockerfile`) carries **only its own stage's dependencies + code**, so a dependency conflict or OOM in one stage can't touch the scheduler. (CeleryExecutor was chosen over DockerOperator to avoid a host Docker socket, which breaks on rootless/LXC/restricted hosts.)

- **prepare** (queue `load`): creates the `raw` schema, opens a `raw.pipeline_runs` row, and writes `watermark.txt` + `run_id.txt` to the shared `pipeline_data` volume. The **load worker owns all DB access**.
- **extract** (queue `extract`): OAuth 2.0 against Fuel Finder, paginated fetch, writes `stations.json`/`prices.json` to the shared volume. Reads `watermark.txt` for the incremental start (DB-free — `requests` only).
- **load** (queue `load`): reads the JSON + `run_id`, writes into the **`raw` schema only** (`raw.stations` upsert, `raw.fuel_prices` append), and completes the pipeline run. `public`/analytics schemas stay untouched until dbt.
- **transform** (queue `transform`): dbt `staging` (views) → `intermediate` (view join layer) → `marts` (tables: `dim_stations`, `fct_fuel_prices`). The app queries the marts.

**Incremental runs**: first run fetches everything; later runs fetch only records changed since the last *completed* run. The watermark is the last completed `raw.pipeline_runs.run_completed_at`, passed from `prepare` to `extract` via `watermark.txt` on the shared volume (empty file = full run).

### dbt specifics

- Profiles read entirely from **env vars** (`DBT_HOST`, `DBT_PORT`, `DBT_USER`, `DBT_PASSWORD`, `DBT_DBNAME`) — nothing hardcoded. See `transform/profiles.yml`.
- The `generate_schema_name` macro uses the custom schema name **verbatim** (no `target_schema_` prefix), so models land in literally `staging` / `intermediate` / `marts`, not prefixed schemas.
- In the transform worker image, dbt lives in an **isolated venv** (`/home/airflow/dbt-venv`, pinned `dbt-core==1.11.11`) to avoid jinja2/click clashes with Airflow; the `transform` `BashOperator` invokes that venv's `dbt build`. The dbt project is **baked into the image** (no volume mount).

## Development workflow

- **TDD at all times** — write the failing test first, then the code to make it pass.
- **Small chunks** — every discrete change is its own commit; do not batch unrelated work.
- **Commit messages** — short, but technically specific about *what* changed and *where* (name the file/module/behaviour), not vague.
- **Branch for everything** — features, fixes, and experiments each get their own branch; keep `main` clean.
- **Always pull before push.**

## Conventions

- Ruff is the linter/formatter: line length 88, double quotes, rules `E`, `F`, `I`, `UP`. `load/ingest.py` is exempt from `E501` (inline SQL).
- Tests live in `tests/` mirroring the package layout; `pythonpath = ["."]` with importlib import mode (configured in `pyproject.toml`).
- The CLI sort keys (`distance`, `e10`, `e5`, `b7s`) are defined in `fnme/constants.py` (`SORT_KV`).
