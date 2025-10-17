@echo off
REM Reset Database - Clear all data and recreate tables
REM WARNING: This will DELETE ALL DATA!

echo.
echo ================================================
echo   10K Insight Agent - Database Reset
echo ================================================
echo.
echo WARNING: This will DELETE ALL DATA in the database!
echo.
echo This will delete:
echo   - All companies
echo   - All analyses
echo   - All pain points
echo   - All product matches
echo   - All pitches
echo   - All jobs
echo.
echo Press Ctrl+C to cancel, or
pause

echo.
echo Checking PostgreSQL status...
docker-compose ps postgres
if %errorlevel% neq 0 (
    echo.
    echo ERROR: PostgreSQL is not running!
    echo Please start it first: docker-compose up -d postgres
    pause
    exit /b 1
)

echo.
echo Stopping API server (if running)...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *uvicorn*" 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Dropping all tables...
type reset_db.sql | docker exec -i tenk_insight_postgres psql -U postgres -d tenk_insight

if %errorlevel% equ 0 (
    echo.
    echo Recreating tables...
    C:\10k-insight-agent\.venv\Scripts\python.exe init_db.py
    
    if %errorlevel% equ 0 (
        echo.
        echo ================================================
        echo   Database Reset Complete!
        echo ================================================
        echo.
        echo Database is now empty and ready for fresh data.
        echo.
        echo Next steps:
        echo   1. Start the application: start_all.bat
        echo   2. Add companies via the UI
        echo   3. Run analyses with the fixed code
        echo.
    ) else (
        echo.
        echo ERROR: Failed to recreate tables
        echo See errors above
    )
) else (
    echo.
    echo ERROR: Failed to drop tables
    echo See errors above
)

pause
