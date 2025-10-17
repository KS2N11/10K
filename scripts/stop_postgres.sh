#!/bin/bash
# Stop PostgreSQL Docker container
# Usage: ./scripts/stop_postgres.sh

set -e

echo "Stopping PostgreSQL..."
docker-compose down

echo ""
echo "✅ PostgreSQL stopped"
echo ""
echo "Note: Data is preserved in Docker volume 'postgres_data'"
echo "To delete data, run: docker-compose down -v"
