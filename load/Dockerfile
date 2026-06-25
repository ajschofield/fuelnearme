# Load worker: Airflow base + the load stage's DB deps and code. This is the
# only stage image that talks to the fuel database.
FROM apache/airflow:2.10.4

COPY load/requirements.txt /tmp/load-requirements.txt
RUN pip install --no-cache-dir -r /tmp/load-requirements.txt

COPY load/ /opt/airflow/load/
ENV PYTHONPATH=/opt/airflow

# Own the shared-volume mountpoint so the named volume is writable by airflow.
USER root
RUN mkdir -p /data && chown airflow /data
USER airflow
