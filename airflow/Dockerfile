FROM apache/airflow:2.9.3
USER airflow
COPY extract/requirements.txt /tmp/extract-req.txt
COPY load/requirements.txt /tmp/load-req.txt
RUN pip install --no-cache-dir \
    -r /tmp/extract-req.txt \
    -r /tmp/load-req.txt \
    "dbt-postgres>=1.10.1"
COPY extract/ /opt/airflow/extract/
COPY load/ /opt/airflow/load/
COPY transform/ /opt/airflow/transform/
ENV PYTHONPATH=/opt/airflow
