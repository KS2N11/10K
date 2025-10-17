@echo off
REM Start PostgreSQL via Docker Compose
REM Usage: scripts\start_postgres.bat

echo Starting PostgreSQL in Docker...
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

REM Start PostgreSQL
docker-compose up -d postgres

REM Wait for PostgreSQL to be ready
echo Waiting for PostgreSQL to be ready...
timeout /t 5 /nobreak >nul

REM Check if PostgreSQL is healthy
docker-compose ps postgres | findstr "healthy" >nul
if %errorlevel% equ 0 (
    echo.
    echo ✅ PostgreSQL is ready!
    echo.
    echo Connection details:
    echo   Host: localhost
    echo   Port: 5432
    echo   Database: tenk_insight
    echo   User: postgres
    echo   Password: postgres
    echo.
    echo DATABASE_URL: postgresql://postgres:postgres@localhost:5432/tenk_insight
    echo.
) else (
    echo.
    echo ⚠️  PostgreSQL is starting... (wait 10 more seconds)
    timeout /t 10 /nobreak >nul
    echo.
    echo Run 'docker-compose ps' to check status
)

pause
