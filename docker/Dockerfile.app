FROM python:3.13-slim

# 1) Set working directory
WORKDIR /app

# 2) Install minimal system deps for curl & PostgreSQL client
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# 3) Copy and install Python deps first (cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 4) Copy only the application code
COPY dash/ ./dash/
COPY templates/ ./templates/
COPY static/ ./static/

# 5) Expose the port your app listens on
EXPOSE 8000

# 6) Healthcheck for Compose readiness
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl --fail http://localhost:8000/health || exit 1

# 7) Final command: run the Flask app
CMD ["gunicorn", "dash.app:server", "--bind", "0.0.0.0:8000", "--workers", "2"]
