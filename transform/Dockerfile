# Transform worker: Airflow base + dbt in an isolated venv. dbt and Airflow pin
# conflicting jinja2/click versions, so dbt lives in its own venv; the transform
# task invokes /home/airflow/dbt-venv/bin/dbt directly.
FROM apache/airflow:2.10.4

# Pin both dbt-core and the adapter to the locked dev versions so the image
# matches what the models were authored and tested against. dbt's packages are
# versioned independently and an unpinned install resolves dbt-core to a beta.
RUN python -m venv /home/airflow/dbt-venv && \
    /home/airflow/dbt-venv/bin/pip install --no-cache-dir \
    "dbt-core==1.11.11" "dbt-postgres==1.10.1"

# Bake the dbt project into the image (no volume mount, #10); chown so dbt can
# write target/ and logs/ as the airflow user at runtime.
COPY --chown=airflow:root transform/ /opt/airflow/transform/
ENV PYTHONPATH=/opt/airflow
