FROM python:3.13-slim
WORKDIR /app
RUN pip install --no-cache-dir dbt-postgres
COPY transform/ transform/
ENV DBT_PROFILES_DIR=/app/transform
CMD ["dbt", "build", "--project-dir", "transform"]
