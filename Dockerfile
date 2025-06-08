# Dockerfile for TransmissionBot
FROM python:3.11-bookworm

WORKDIR /app

# Install build dependencies for pip (if needed by any package)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Healthcheck: ensure the bot process is running (PID 1)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD pgrep -f 'python bot.py' || exit 1

CMD ["python", "bot.py"] 