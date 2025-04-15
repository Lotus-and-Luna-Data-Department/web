FROM python:3.9-slim

WORKDIR /app

# Install system packages, including curl
RUN apt-get update && apt-get install -y curl

# Copy your code
COPY dash/app.py /app/app.py
COPY dash/requirements.txt /app/requirements.txt

# Install python packages
RUN pip install --no-cache-dir -r /app/requirements.txt

# Expose port 8000
EXPOSE 8000

CMD ["python", "/app/app.py"]
