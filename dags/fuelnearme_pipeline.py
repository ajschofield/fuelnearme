from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

import sqlalchemy as sql
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

_DATABASE_URL = os.environ.get("DATABASE_URL", "")
_DATA_DIR = Path("/tmp/fuelnearme_pipeline")


def _extract(**context) -> bool:
    from extract.main import main as run_extract
    from load.ingest import get_last_run_timestamp
    from load.schema import create_raw_schema

    engine = sql.create_engine(_DATABASE_URL)
    create_raw_schema(engine)
    timestamp = get_last_run_timestamp(engine)

    run_extract(
        output_dir=_DATA_DIR,
        effective_start_timestamp=timestamp,
        client_id=os.environ["CLIENT_ID"],
        client_secret=os.environ["CLIENT_SECRET"],
    )
    return timestamp is not None  # pushed to XCom as is_incremental


def _load(**context) -> None:
    from load.main import main as run_load

    is_incremental = context["ti"].xcom_pull(task_ids="extract")
    engine = sql.create_engine(_DATABASE_URL)
    run_load(engine=engine, input_dir=_DATA_DIR, is_incremental=bool(is_incremental))


with DAG(
    dag_id="fuelnearme_pipeline",
    description="Hourly extract, load and transform of UK fuel price data",
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "email_on_failure": False,
    },
    schedule="@hourly",
    start_date=datetime(2026, 6, 21),
    catchup=False,
    tags=["fuelnearme"],
) as dag:
    extract = PythonOperator(
        task_id="extract",
        python_callable=_extract,
    )

    load = PythonOperator(
        task_id="load",
        python_callable=_load,
    )

    transform = BashOperator(
        task_id="transform",
        bash_command=(
            "dbt build "
            "--profiles-dir /opt/airflow/transform "
            "--project-dir /opt/airflow/transform"
        ),
    )

    extract >> load >> transform
