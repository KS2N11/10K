FROM python:3.11

# Make Python output unbuffered and avoid writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////app/dev.db

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:${PATH}"

COPY . /app

RUN uv pip install --system --no-cache .

EXPOSE 8000

# Copy and prepare startup script
COPY startup.sh /app/startup.sh
# Ensure it's executable and convert CRLF to LF to avoid bash issues
RUN chmod +x /app/startup.sh && sed -i 's/\r$//' /app/startup.sh

CMD ["bash", "/app/startup.sh"]
