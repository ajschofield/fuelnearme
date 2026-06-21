FROM apache/airflow:2.10.4
USER airflow
COPY extract/requirements.txt /tmp/extract-req.txt
COPY load/requirements.txt /tmp/load-req.txt
RUN pip install --no-cache-dir \
    -r /tmp/extract-req.txt \
    -r /tmp/load-req.txt \
    "sqlalchemy>=1.4,<2.0"
RUN python -m venv /home/airflow/dbt-venv && \
    /home/airflow/dbt-venv/bin/pip install --no-cache-dir dbt-postgres
COPY extract/ /opt/airflow/extract/
COPY load/ /opt/airflow/load/
COPY --chown=airflow:root transform/ /opt/airflow/transform/
ENV PYTHONPATH=/opt/airflow
