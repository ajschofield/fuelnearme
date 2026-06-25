from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# Shared named volume mounted into the extract + load workers. The scheduler
# only parses this file, so it must import nothing from the stage packages at
# module scope — every stage import happens inside the callables below, which
# run on the worker whose image carries that stage's dependencies.
_DATA_DIR = Path("/data")
_DBT_PROJECT = "/opt/airflow/transform"


def _prepare(**context) -> None:
    import sqlalchemy as sql

    from load.main import prepare, read_secret

    engine = sql.create_engine(read_secret("DATABASE_URL"))
    prepare(engine, _DATA_DIR)


def _extract(**context) -> None:
    from extract.main import main as run_extract
    from extract.main import read_secret

    run_extract(
        output_dir=_DATA_DIR,
        client_id=read_secret("CLIENT_ID"),
        client_secret=read_secret("CLIENT_SECRET"),
    )


def _load(**context) -> None:
    import sqlalchemy as sql

    from load.main import ingest, read_secret

    engine = sql.create_engine(read_secret("DATABASE_URL"))
    ingest(engine, _DATA_DIR)


with DAG(
    dag_id="fuelnearme_pipeline",
    description="30-minute extract, load and transform of UK fuel price data",
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "email_on_failure": False,
    },
    schedule="*/30 * * * *",
    start_date=datetime(2026, 6, 21),
    catchup=False,
    max_active_runs=1,
    tags=["fuelnearme"],
) as dag:
    prepare = PythonOperator(
        task_id="prepare",
        python_callable=_prepare,
        queue="load",
    )

    extract = PythonOperator(
        task_id="extract",
        python_callable=_extract,
        queue="extract",
    )

    load = PythonOperator(
        task_id="load",
        python_callable=_load,
        queue="load",
    )

    transform = BashOperator(
        task_id="transform",
        bash_command=(
            # In prod DBT_PASSWORD comes from a docker secret file; in dev it
            # falls back to the plain DBT_PASSWORD env. dbt itself only reads env.
            'export DBT_PASSWORD="$(cat "$DBT_PASSWORD_FILE" 2>/dev/null '
            '|| printf %s "$DBT_PASSWORD")"; '
            f"/home/airflow/dbt-venv/bin/dbt build --project-dir {_DBT_PROJECT} "
            f"--profiles-dir {_DBT_PROJECT} --log-path /tmp/dbt-logs"
        ),
        queue="transform",
    )

    prepare >> extract >> load >> transform
