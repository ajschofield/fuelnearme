FROM python:3.13-slim
WORKDIR /app
COPY extract/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY extract/ extract/
CMD ["python", "-m", "extract.main"]
