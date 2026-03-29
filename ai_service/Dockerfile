FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt fastapi uvicorn
COPY main.py .

CMD ["uvicorn", "main:fastapi_app", "--host", "0.0.0.0", "--port", "8000"]
