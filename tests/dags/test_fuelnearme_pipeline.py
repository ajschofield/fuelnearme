from pathlib import Path

import pytest

pytest.importorskip("airflow.models", reason="apache-airflow not installed — skipping DAG tests")

DAGS_DIR = Path(__file__).parents[2] / "dags"


@pytest.fixture(autouse=True)
def airflow_home(monkeypatch, tmp_path):
    monkeypatch.setenv("AIRFLOW_HOME", str(tmp_path))


def _dagbag():
    from airflow.models import DagBag
    return DagBag(dag_folder=str(DAGS_DIR), include_examples=False)


def test_dag_loads_without_errors():
    dagbag = _dagbag()
    assert dagbag.import_errors == {}, dagbag.import_errors
    assert "fuelnearme_pipeline" in dagbag.dags


def test_dag_has_correct_tasks():
    dag = _dagbag().dags["fuelnearme_pipeline"]
    assert {t.task_id for t in dag.tasks} == {"extract", "load", "transform"}


def test_dag_is_hourly():
    dag = _dagbag().dags["fuelnearme_pipeline"]
    assert dag.schedule_interval == "@hourly"


def test_task_dependencies_are_sequential():
    dag = _dagbag().dags["fuelnearme_pipeline"]
    assert dag.get_task("load").upstream_task_ids == {"extract"}
    assert dag.get_task("transform").upstream_task_ids == {"load"}
