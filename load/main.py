from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import sqlalchemy as sql

from load.ingest import (
    complete_pipeline_run,
    get_last_run_timestamp,
    ingest_prices,
    ingest_stations,
    start_pipeline_run,
)
from load.schema import create_raw_schema


def prepare(engine: sql.Engine, data_dir: Path) -> None:
    """Create the raw schema and open a pipeline run.

    Writes two handoff files to the shared volume for the downstream stages:
    `watermark.txt` (the last completed run's timestamp, empty on a full run)
    which extract reads, and `run_id.txt` which ingest completes.
    """
    data_dir = Path(data_dir)

    create_raw_schema(engine)
    timestamp = get_last_run_timestamp(engine)
    run_id = start_pipeline_run(engine, is_incremental=timestamp is not None)

    (data_dir / "watermark.txt").write_text(timestamp or "")
    (data_dir / "run_id.txt").write_text(str(run_id))


def ingest(engine: sql.Engine, data_dir: Path) -> None:
    """Load the extracted JSON into the raw schema and close the pipeline run."""
    data_dir = Path(data_dir)

    run_id = int((data_dir / "run_id.txt").read_text())
    stations = json.loads((data_dir / "stations.json").read_text())
    prices = json.loads((data_dir / "prices.json").read_text())

    ingest_stations(engine, stations)
    ingest_prices(engine, prices)
    complete_pipeline_run(engine, run_id)

    print(f"Loaded {len(stations)} stations and {len(prices)} price records.")


_COMMANDS = {"prepare": prepare, "ingest": ingest}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in _COMMANDS:
        raise SystemExit(f"usage: python -m load.main {{{'|'.join(_COMMANDS)}}}")

    engine = sql.create_engine(os.environ["DATABASE_URL"])
    data_dir = Path(os.getenv("DATA_DIR", "/data"))
    _COMMANDS[sys.argv[1]](engine, data_dir)


if __name__ == "__main__":
    main()
