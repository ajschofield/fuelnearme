import os
import subprocess
import sys
from pathlib import Path

import sqlalchemy as sql

from extract.main import main as run_extract
from load.ingest import get_last_run_timestamp
from load.main import main as run_load
from load.schema import create_raw_schema

DATABASE_URL = os.environ["DATABASE_URL"]
DBT_PROFILES_DIR = Path(__file__).parent / "transform"
DBT_PROJECT_DIR = Path(__file__).parent / "transform"


def run_dbt() -> None:
    result = subprocess.run(
        ["dbt", "build", "--profiles-dir", str(DBT_PROFILES_DIR), "--project-dir", str(DBT_PROJECT_DIR)],
        check=False,
    )
    if result.returncode != 0:
        print("[pipeline] dbt build failed.")
        sys.exit(result.returncode)


def main() -> None:
    engine = sql.create_engine(DATABASE_URL)
    create_raw_schema(engine)

    timestamp = get_last_run_timestamp(engine)
    is_incremental = timestamp is not None

    if is_incremental:
        print(f"[pipeline] Incremental run from {timestamp}.")
    else:
        print("[pipeline] Full load (no previous run found).")

    data_dir = Path(os.getenv("DATA_DIR", "/tmp/pipeline_data"))

    run_extract(output_dir=data_dir, effective_start_timestamp=timestamp)
    run_load(engine=engine, input_dir=data_dir, is_incremental=is_incremental)
    run_dbt()

    print("[pipeline] Done.")


if __name__ == "__main__":
    main()
