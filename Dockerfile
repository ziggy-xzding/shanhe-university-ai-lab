FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8801

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8801

CMD ["sh", "-c", "uvicorn main:app --host ${APP_HOST:-0.0.0.0} --port ${APP_PORT:-8801}"]
