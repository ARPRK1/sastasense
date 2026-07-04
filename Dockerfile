# SastaSense — production container
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LIVE_SCRAPING=true \
    DEMO_FALLBACK=true

WORKDIR /app

# Install deps first (better build caching)
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

# Copy the whole project (backend + frontend)
COPY . .

WORKDIR /app/backend

# Hosts inject $PORT; default to 8000 locally.
ENV PORT=8000
EXPOSE 8000

# Shell form so $PORT expands at runtime.
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT}
