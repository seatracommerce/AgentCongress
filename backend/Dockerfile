FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Preserve backend package so "from backend.xxx" works (and for Cloud Run)
COPY . ./backend
ENV PYTHONPATH=/app

# Cloud Run expects PORT=8080; use that as default so the container always listens correctly
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
