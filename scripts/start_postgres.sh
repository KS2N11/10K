#!/bin/bash
# Start PostgreSQL via Docker Compose
# Usage: ./scripts/start_postgres.sh

set -e

echo "Starting PostgreSQL in Docker..."
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ ERROR: Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

# Start PostgreSQL
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Check if PostgreSQL is healthy
if docker-compose ps postgres | grep -q "healthy"; then
    echo ""
    echo "✅ PostgreSQL is ready!"
    echo ""
    echo "Connection details:"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo "  Database: tenk_insight"
    echo "  User: postgres"
    echo "  Password: postgres"
    echo ""
    echo "DATABASE_URL: postgresql://postgres:postgres@localhost:5432/tenk_insight"
    echo ""
else
    echo ""
    echo "⚠️  PostgreSQL is starting... (wait 10 more seconds)"
    sleep 10
    echo ""
    echo "Run 'docker-compose ps' to check status"
fi
