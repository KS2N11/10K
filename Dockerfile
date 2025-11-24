FROM python:3.11

# Make Python output unbuffered and avoid writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////app/dev.db

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt pyproject.toml ./

# Install dependencies using pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app

EXPOSE 8000

# Copy and prepare startup script
COPY startup.sh /app/startup.sh
# Ensure it's executable and convert CRLF to LF to avoid bash issues
RUN chmod +x /app/startup.sh && sed -i 's/\r$//' /app/startup.sh

CMD ["bash", "/app/startup.sh"]
