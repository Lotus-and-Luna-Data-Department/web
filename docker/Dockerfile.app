FROM python:3.10-slim

WORKDIR /app
ENV PYTHONPATH=/app       

# Install system deps for curl, PostgreSQL, and Python build tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
       libpq-dev \
       gcc \
       python3-dev \
       build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy & install Python deps
COPY requirements.txt .
# Preinstall setuptools & wheel so pip can build any wheels
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY webapp/ ./webapp/

# Expose port
EXPOSE 8000

# Healthcheck endpoint
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl --fail http://localhost:8000/health || exit 1

# Run the app
CMD ["python", "webapp/app.py"]
