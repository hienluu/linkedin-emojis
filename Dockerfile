# Cloud Run image. Mirrors the Modal runtime (Python 3.12) so behaviour matches.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first so edits to the app don't invalidate the layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py search.py concepts.py compose.py config.py guard.py ./
COPY data/emojis.json ./data/emojis.json
COPY static/ ./static/

# Cloud Run injects PORT (8080 by default) and terminates TLS for us.
ENV PORT=8080
EXPOSE 8080

# Shell form so ${PORT} expands; exec so uvicorn is PID 1 and gets SIGTERM.
CMD exec uvicorn app:api --host 0.0.0.0 --port ${PORT} --workers 1
