FROM python:3.13-slim
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
COPY .streamlit/ .streamlit/
ENV PYTHONPATH=/app
EXPOSE 8501
CMD ["streamlit", "run", "app/main.py", "--server.address", "0.0.0.0", "--server.headless", "true"]
