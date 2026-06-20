FROM python:3.13-slim
WORKDIR /app
COPY load/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY load/ load/
CMD ["python", "-m", "load.main"]
