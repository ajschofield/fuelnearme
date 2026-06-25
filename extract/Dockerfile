# Extract worker: Airflow base + only the extract stage's deps and code.
FROM apache/airflow:2.10.4

COPY extract/requirements.txt /tmp/extract-requirements.txt
RUN pip install --no-cache-dir -r /tmp/extract-requirements.txt

COPY extract/ /opt/airflow/extract/
ENV PYTHONPATH=/opt/airflow

# Own the shared-volume mountpoint so the named volume is writable by airflow.
USER root
RUN mkdir -p /data && chown airflow /data
USER airflow
