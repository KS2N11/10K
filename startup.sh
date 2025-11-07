#!/bin/bash

echo "Initializing database..."
python init_db.py || echo "Note: Database initialization skipped (tables may already exist)"

echo "Starting application..."
exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8000