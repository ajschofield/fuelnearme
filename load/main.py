from __future__ import annotations

import json
import os
from pathlib import Path

import sqlalchemy as sql

from load.ingest import complete_pipeline_run, ingest_prices, ingest_stations, start_pipeline_run
from load.schema import create_raw_schema


def main(
    engine: sql.Engine,
    input_dir: Path = Path("/data"),
    is_incremental: bool = False,
) -> None:
    input_dir = Path(input_dir)

    create_raw_schema(engine)

    run_id = start_pipeline_run(engine, is_incremental=is_incremental)

    stations = json.loads((input_dir / "stations.json").read_text())
    prices = json.loads((input_dir / "prices.json").read_text())

    ingest_stations(engine, stations)
    ingest_prices(engine, prices)

    complete_pipeline_run(engine, run_id)

    print(f"Loaded {len(stations)} stations and {len(prices)} price records.")


if __name__ == "__main__":
    engine = sql.create_engine(os.environ["DATABASE_URL"])
    main(
        engine=engine,
        input_dir=Path(os.getenv("INPUT_DIR", "/data")),
    )
