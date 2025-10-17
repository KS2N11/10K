@echo off
REM Stop PostgreSQL Docker container
REM Usage: scripts\stop_postgres.bat

echo Stopping PostgreSQL...
docker-compose down

echo.
echo ✅ PostgreSQL stopped
echo.
echo Note: Data is preserved in Docker volume 'postgres_data'
echo To delete data, run: docker-compose down -v
pause
