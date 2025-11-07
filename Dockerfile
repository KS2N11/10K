FROM python:3.11

# Make Python output unbuffered and avoid writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # Safe default so the app can boot without Postgres
    DATABASE_URL=sqlite:////app/dev.db

WORKDIR /app

# Install system dependencies, netcat for db checks, and uv (fast Python package manager)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl netcat-traditional && \
    rm -rf /var/lib/apt/lists/* && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

# Ensure uv is on PATH
ENV PATH="/root/.local/bin:${PATH}"

# Copy application source first (editable install expects sources present)
COPY . /app

# Install project dependencies using uv
# Use non-editable install by default for reliability; dev can mount volumes
RUN uv pip install --system --no-cache .

# Expose backend port
EXPOSE 8000

# Copy and set up startup script
COPY startup.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/startup.sh

# Use startup script as default command
CMD ["/usr/local/bin/startup.sh"]
