#!/bin/bash

echo "Starting backend container..."
echo "DATABASE_URL is set to: $DATABASE_URL"

# Extract host and port from DATABASE_URL
if [[ $DATABASE_URL =~ postgres[ql]?://[^:]+:[^@]+@([^:]+):([0-9]+)/.*$ ]]; then
    DB_HOST="${BASH_REMATCH[1]}"
    DB_PORT="${BASH_REMATCH[2]}"
    echo "Extracted database host: $DB_HOST"
    echo "Extracted database port: $DB_PORT"
else
    echo "Error: Could not parse DATABASE_URL: $DATABASE_URL"
    echo "Expected format: postgresql://user:password@host:port/dbname"
    exit 1
fi

# Wait for postgres to be ready
echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
max_attempts=30
attempt=0

while ! nc -z $DB_HOST $DB_PORT; do
    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        echo "Error: Could not connect to PostgreSQL after $max_attempts attempts"
        exit 1
    fi
    echo "Attempt $attempt/$max_attempts: PostgreSQL at $DB_HOST:$DB_PORT is not ready - waiting 2 seconds..."
    sleep 2
done

echo "PostgreSQL is up - attempting to initialize database..."

# Try to run initialization, but don't fail if tables already exist
python init_db.py || {
    echo "Note: Database initialization returned non-zero exit code."
    echo "If tables already exist, this is normal and can be ignored."
}

echo "Starting FastAPI application..."
exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8000