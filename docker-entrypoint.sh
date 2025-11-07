#!/bin/bash

# Wait for postgres to be ready
echo "Waiting for PostgreSQL to be ready..."
while ! curl -s "http://postgres:5432" >/dev/null; do
  sleep 1
done

# Initialize the database
echo "Initializing database..."
python init_db.py

# Start the application
echo "Starting application..."
exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8000