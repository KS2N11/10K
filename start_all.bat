@echo off
echo ============================================
echo Starting 10K Insight Agent (React + FastAPI)
echo ============================================
echo.

echo [1/3] Starting PostgreSQL...
docker-compose up -d
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo Waiting for PostgreSQL to be ready...
timeout /t 10 /nobreak >nul

echo.
echo [2/3] Starting FastAPI Backend...
start "10K Insight API" cmd /k ".venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload"

echo Waiting for API server to start...
timeout /t 5 /nobreak >nul

echo.
echo [3/3] Starting React Frontend...
start "10K Insight UI" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================
echo All services started successfully!
echo ============================================
echo.
echo React UI:    http://localhost:3000
echo API Server:  http://127.0.0.1:8000
echo API Docs:    http://127.0.0.1:8000/docs
echo PostgreSQL:  localhost:5432
echo.
echo Press any key to exit...
pause >nul
