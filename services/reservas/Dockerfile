FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY database.py .
COPY models.py .
COPY circuit_breaker.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]