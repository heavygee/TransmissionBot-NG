# Dockerfile for TransmissionBot
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Create DB initialization script
RUN echo '#!/bin/bash\necho "Checking database directory..."\nmkdir -p /app\ntouch /app/transbotdata.db\nchmod 666 /app/transbotdata.db\necho "Database file ready."\n' > /init-db.sh && \
    chmod +x /init-db.sh

# Create simple healthcheck script
RUN echo '#!/bin/bash\npgrep -f "python bot.py" > /dev/null\nif [ $? -ne 0 ]; then\n  exit 1\nfi\nGET_ME=$(grep -c "wait_until_ready" bot.py)\nif [ "$GET_ME" -eq 0 ]; then\n  exit 1\nfi\nexit 0\n' > /healthcheck.sh && \
    chmod +x /healthcheck.sh

# Healthcheck: ensure the bot process is running and code is valid
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD /healthcheck.sh

# Run the init script before starting the bot
CMD ["/bin/bash", "-c", "/init-db.sh && python bot.py"] 